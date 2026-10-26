#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <gl/GL.h>
#include <map>
#include <string>
#include <vector>
#include "localization_core.hpp"

namespace avzh {
inline std::wstring utf8(const std::string& text){
    int count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);
    if(count<=0 && !text.empty())throw std::runtime_error("Invalid UTF-8 translation");
    std::wstring out(count,L'\0');if(count)MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),&out[0],count);return out;
}
struct TextState { int align=0,font=12,left=0,top=0,right=0,bottom=0,screen_width=0,screen_height=0;int clip_left=0,clip_top=0,clip_right=0,clip_bottom=0;bool clip=true;float red=1,green=1,blue=1,alpha=1; };
struct TextResult { int height=0,last_x=0,last_y=0; };
struct BitmapText { GLuint texture=0;int width=0,height=0,texture_width=0,texture_height=0; };
class Renderer {
    HDC dc_=nullptr;std::map<int,HFONT> fonts_;
    HGLRC context_=nullptr;std::map<std::pair<int,std::wstring>,BitmapText> textures_;
    int select(int height){
        if(!dc_)dc_=CreateCompatibleDC(nullptr);
        if(!dc_)throw std::runtime_error("Cannot create font DC");
        auto it=fonts_.find(height);if(it==fonts_.end()){
            HFONT font=CreateFontW(height,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,L"Microsoft YaHei");
            if(!font)throw std::runtime_error("Cannot create CJK font");it=fonts_.emplace(height,font).first;
        }
        SelectObject(dc_,it->second);return height;
    }
    static int power2(int value){int n=1;while(n<value && n<8192)n*=2;return n;}
    const BitmapText& bitmap(const std::wstring& text,int height){
        HGLRC now=wglGetCurrentContext();if(!now)throw std::runtime_error("No current GL context");
        if(context_!=now){textures_.clear();context_=now;}
        const auto key=std::make_pair(height,text);auto found=textures_.find(key);if(found!=textures_.end())return found->second;
        if(textures_.size()>=512){for(const auto& entry:textures_)glDeleteTextures(1,&entry.second.texture);textures_.clear();}
        select(height);SIZE extent{};if(!GetTextExtentPoint32W(dc_,text.data(),static_cast<int>(text.size()),&extent))throw std::runtime_error("Cannot measure CJK text");
        BitmapText item;item.width=std::max(1,static_cast<int>(extent.cx));item.height=height;item.texture_width=power2(item.width+2);item.texture_height=power2(height+2);
        GLint max_size=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&max_size);if(item.texture_width>max_size || item.texture_height>max_size)throw std::runtime_error("Text exceeds GL texture limit");
        BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=item.texture_width;info.bmiHeader.biHeight=-item.texture_height;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
        void* bits=nullptr;HBITMAP dib=CreateDIBSection(dc_,&info,DIB_RGB_COLORS,&bits,nullptr,0);if(!dib || !bits)throw std::runtime_error("Cannot rasterize CJK text");
        HGDIOBJ old=SelectObject(dc_,dib);size_t bytes=static_cast<size_t>(item.texture_width)*item.texture_height*4;memset(bits,0,bytes);SetTextColor(dc_,RGB(255,255,255));SetBkMode(dc_,TRANSPARENT);
        BOOL rendered=TextOutW(dc_,1,1,text.data(),static_cast<int>(text.size()));GdiFlush();
        std::vector<unsigned char> rgba(bytes);const auto* input=static_cast<const unsigned char*>(bits);
        for(size_t i=0;i<bytes;i+=4){rgba[i]=rgba[i+1]=rgba[i+2]=255;rgba[i+3]=std::max(input[i],std::max(input[i+1],input[i+2]));}
        SelectObject(dc_,old);DeleteObject(dib);if(!rendered)throw std::runtime_error("Cannot draw CJK glyphs");
        glGenTextures(1,&item.texture);glBindTexture(GL_TEXTURE_2D,item.texture);glPixelStorei(GL_UNPACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ROW_LENGTH,0);glPixelStorei(GL_UNPACK_SKIP_ROWS,0);glPixelStorei(GL_UNPACK_SKIP_PIXELS,0);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,item.texture_width,item.texture_height,0,GL_RGBA,GL_UNSIGNED_BYTE,rgba.data());glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
        return textures_.emplace(key,item).first->second;
    }
public:
    int measure(const std::wstring& text,int height){select(height);SIZE size{};if(!GetTextExtentPoint32W(dc_,text.data(),static_cast<int>(text.size()),&size))throw std::runtime_error("Cannot measure text");return size.cx;}
    std::wstring face(){select(13);wchar_t name[128]{};GetTextFaceW(dc_,128,name);return name;}
    bool glyphs(const std::wstring& text){select(13);std::vector<WORD> glyph(text.size());if(GetGlyphIndicesW(dc_,text.data(),static_cast<int>(text.size()),glyph.data(),GGI_MARK_NONEXISTING_GLYPHS)==GDI_ERROR)return false;return std::find(glyph.begin(),glyph.end(),0xffff)==glyph.end();}
    TextResult draw(std::wstring text,const TextState& state){
        if(!wglGetCurrentContext())throw std::runtime_error("No GL context");
        int size=state.font;switch(size){case 14:case 15:break;case 16:case 18:size=16;break;case 20:case 22:case 24:size=24;break;default:size=12;}
        const int step=size+1;int align=state.align;if(align==2 && text.find(L'|')!=std::wstring::npos)align=0;
        std::vector<std::wstring> lines=align==0?wrap(text,std::max(1,state.right-state.left-6),[&](const std::wstring& s){return measure(s,step);}):std::vector<std::wstring>{text};
        int y=state.top+2;if(align==1)y=(state.top+state.bottom-step)/2+2;
        glPushAttrib(GL_ALL_ATTRIB_BITS);glPushClientAttrib(GL_CLIENT_PIXEL_STORE_BIT);
        try{
            const char* extensions=reinterpret_cast<const char*>(glGetString(GL_EXTENSIONS));if(extensions && (strstr(extensions,"GL_ARB_texture_rectangle") || strstr(extensions,"GL_EXT_texture_rectangle") || strstr(extensions,"GL_NV_texture_rectangle")))glDisable(0x84f5);
            glEnable(GL_TEXTURE_2D);glEnable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_LIGHTING);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE);glColor4f(state.red,state.green,state.blue,state.alpha);
            if(state.clip){GLint viewport[4];glGetIntegerv(GL_VIEWPORT,viewport);double sx=static_cast<double>(viewport[2])/std::max(1,state.screen_width),sy=static_cast<double>(viewport[3])/std::max(1,state.screen_height);glEnable(GL_SCISSOR_TEST);glScissor(viewport[0]+static_cast<GLint>(state.clip_left*sx),viewport[1]+static_cast<GLint>((state.screen_height-state.clip_bottom)*sy),std::max(0,static_cast<int>((state.clip_right-state.clip_left)*sx)),std::max(0,static_cast<int>((state.clip_bottom-state.clip_top)*sy)));}
            TextResult result;result.height=step*static_cast<int>(lines.size());
            for(const auto& line:lines){int width=measure(line,step),x=state.left+2;if(align==1)x=(state.left+state.right-width)/2+2;
                if(!line.empty()){
                    const auto& image=bitmap(line,step);glBindTexture(GL_TEXTURE_2D,image.texture);
                    const float l=static_cast<float>(x-1),t=static_cast<float>(state.screen_height-y+1),r=l+image.width+2,b=t-image.height-2;
                    const float u=static_cast<float>(image.width+2)/image.texture_width,v=static_cast<float>(image.height+2)/image.texture_height;
                    glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2f(l,t);glTexCoord2f(0,v);glVertex2f(l,b);glTexCoord2f(u,v);glVertex2f(r,b);glTexCoord2f(u,0);glVertex2f(r,t);glEnd();
                }result.last_x=x;result.last_y=y;y+=step;
            }
            glPopClientAttrib();glPopAttrib();return result;
        }catch(...){glPopClientAttrib();glPopAttrib();throw;}
    }
};
} // namespace avzh
