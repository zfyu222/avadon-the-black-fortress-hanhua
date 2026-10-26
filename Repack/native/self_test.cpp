#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <mmsystem.h>
#include <gl/GL.h>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iterator>
#include "renderer.hpp"
#include "forward_metadata.hpp"

extern "C" void FixtureInitialize(void*,const wchar_t*,const wchar_t*);
extern "C" void FixtureFinish();
extern "C" bool FixtureNameExpansion();
static void require(bool test,const char* reason){if(!test)throw std::runtime_error(reason);}

static int call_text(void* entry,const char* text,unsigned alignment){
    unsigned before=0,after=0,saved_bx=0,saved_si=0,saved_di=0;int value=0;
    __asm {
        mov before,esp
        mov ebx,0x11223344
        mov esi,0x55667788
        mov edi,0x99aabbcc
        push 0x012c008c
        push 0x000a000a
        push 31
        push 31
        push 31
        push 16
        mov eax,text
        push eax
        mov ecx,alignment
        mov eax,entry
        call eax
        add esp,28
        mov value,eax
        mov after,esp
        mov saved_bx,ebx
        mov saved_si,esi
        mov saved_di,edi
    }
    require(before==after,"Text ABI stack cleanup mismatch");require(saved_bx==0x11223344 && saved_si==0x55667788 && saved_di==0x99aabbcc,"Text ABI nonvolatile register mismatch");return value;
}
static int call_measure(void* entry,const char* text){
    unsigned before=0,after=0;int value=0;
    __asm {
        mov before,esp
        mov edx,text
        mov eax,entry
        call eax
        mov value,eax
        mov after,esp
    }
    require(before==after,"Measure ABI stack cleanup mismatch");return value;
}
int wmain(int argc,wchar_t** argv){
    if(argc!=5){std::cerr<<"self_test <dictionary> <glyphs> <proxy dll> <output directory>\n";return 2;}
    const std::wstring output=argv[4];
    try{
        avzh::Dictionary dictionary;dictionary.load(argv[1]);std::string value;
        require(dictionary.size()>=15928,"Incomplete dictionary");require(dictionary.lookup("Blademaster",value),"Exact lookup failed");require(!avzh::utf8(value).empty(),"UTF8 decode failed");
        require(dictionary.lookup("Your Coins: 321",value) && value.find("321")!=std::string::npos && value.find("%d")==std::string::npos,"Numeric formatted lookup failed");
        require(!dictionary.lookup("Your Coins: ff",value),"Numeric pattern accepted nonnumeric value");
        require(!dictionary.lookup("AVZH_COMPLETELY_UNMATCHED_371",value),"Unknown lookup must stay unknown");
        const char* quoted="\"You will soon learn that, in Avadon, you are told only what you need to know. This is for your protection and ours.\"";
        require(dictionary.lookup(quoted,value) && value.find('_')==std::string::npos && value.find('"')!=std::string::npos,"Script quote display variant failed");
        require(dictionary.lookup("Choosing a Character Type",value) && value.find('$')==std::string::npos,"Manual heading display variant failed");
        avzh::Dictionary generic;generic.add("%s %s %s","%s %s %s");generic.prepare();require(!generic.lookup("one two three",value),"Unbound generic format matched prose");
        const char* dialogue_choices[]={"(Watch them quietly.)","(Back away.)","Ummm ... Could you control those ... things?"};
        for(int i=0;i<3;++i){std::string plain,numbered;require(dictionary.lookup(dialogue_choices[i],plain),"Approved choice absent");std::string prefix=std::to_string(i+1)+". ";require(dictionary.lookup(prefix+dialogue_choices[i],numbered) && numbered==prefix+plain,"Numbered dialogue choice failed");}
        require(!dictionary.lookup("1. AVZH_UNKNOWN_CHOICE_391",value),"Unknown choice must fall back");
        require(!dictionary.lookup("01. (Back away.)",value),"Malformed leading zero must not be stripped");
        require(!dictionary.lookup("100. (Back away.)",value),"Unobserved three-digit prefix must not match");
        avzh::Dictionary priority;priority.add("Body","Inner");priority.add("1. Body","Exact");require(priority.lookup("1. Body",value) && value=="Exact","Canonical numbered record must win");
        std::ofstream choice_report((output+L"\\dialogue_choice_report.json").c_str(),std::ios::binary);
        choice_report<<"{\"status\":\"passed\",\"reported_choices\":3,\"exact_record_priority\":true,\"unknown_and_malformed_fall_back\":true,\"game_started\":false}\n";choice_report.close();
        auto lines=avzh::wrap(L"甲乙丙丁，戊己。",3,[](const std::wstring&s){return static_cast<int>(s.size());});for(const auto& line:lines)require(line.empty() || !avzh::closing(line[0]),"Closing punctuation starts wrapped line");
        std::wstring host_path=argv[0];auto slash=host_path.find_last_of(L"\\/");require(slash!=std::wstring::npos,"Need absolute component host path");
        std::wstring startup_dir=host_path.substr(0,slash)+L"\\AvadonChinese";CreateDirectoryW(startup_dir.c_str(),nullptr);
        std::wstring startup_log=startup_dir+L"\\runtime.log";DeleteFileW(startup_log.c_str());
        HMODULE proxy=LoadLibraryW(argv[3]);require(proxy!=nullptr,"Cannot load built x86 proxy");
        bool bootstrapped=false;
        // Do not resolve or invoke timeGetTime until the independent bootstrap
        // has logged its unsupported-host decision. This catches the old bug.
        for(int attempt=0;attempt<150 && !bootstrapped;++attempt){
            std::ifstream file(startup_log.c_str(),std::ios::binary);std::string log((std::istreambuf_iterator<char>(file)),{});
            bootstrapped=log.find("unsupported executable: forwarding only")!=std::string::npos;
            if(!bootstrapped)Sleep(20);
        }
        require(bootstrapped,"Adapter never initialized without timeGetTime");
        std::ofstream bootstrap_report((output+L"\\bootstrap_report.json").c_str(),std::ios::binary);
        bootstrap_report<<"{\"status\":\"passed\",\"startup_without_timeGetTime\":true,\"game_started\":false}\n";bootstrap_report.close();
        for(unsigned i=0;i<AVZH_FORWARD_COUNT;++i)require(GetProcAddress(proxy,avzh_forward_names[i]?avzh_forward_names[i]:MAKEINTRESOURCEA(avzh_forward_ordinals[i]))!=nullptr,"Forwarding export missing");
        auto clock=reinterpret_cast<DWORD(WINAPI*)()>(GetProcAddress(proxy,"timeGetTime"));DWORD tick=clock();require(std::abs(static_cast<int32_t>(tick-GetTickCount()))<1000,"Clock forwarding differs from system clock");
        auto caps=reinterpret_cast<MMRESULT(WINAPI*)(LPTIMECAPS,UINT)>(GetProcAddress(proxy,"timeGetDevCaps"));TIMECAPS capabilities{};require(caps(&capabilities,sizeof(capabilities))==0 && capabilities.wPeriodMin>0,"Argument-bearing stdcall forwarding failed");
        // A private memory DIB runs the GL/GDI component test. No desktop
        // capture, visible window, Avadon launch or game code is involved.
        HDC dc=CreateCompatibleDC(nullptr);require(dc!=nullptr,"Cannot create offscreen DC");BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=320;info.bmiHeader.biHeight=-160;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;void* dib_bits=nullptr;
        HBITMAP dib=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&dib_bits,nullptr,0);require(dib!=nullptr,"Cannot create offscreen DIB");HGDIOBJ old=SelectObject(dc,dib);
        PIXELFORMATDESCRIPTOR format{};format.nSize=sizeof(format);format.nVersion=1;format.dwFlags=PFD_DRAW_TO_BITMAP|PFD_SUPPORT_OPENGL|PFD_SUPPORT_GDI;format.iPixelType=PFD_TYPE_RGBA;format.cColorBits=32;format.cDepthBits=0;format.iLayerType=PFD_MAIN_PLANE;int pixel_format=ChoosePixelFormat(dc,&format);require(pixel_format!=0 && SetPixelFormat(dc,pixel_format,&format),"Offscreen GL pixel format unavailable");HGLRC context=wglCreateContext(dc);require(context && wglMakeCurrent(dc,context),"Offscreen GL context unavailable");
        glViewport(0,0,320,160);glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,320,0,160,-100,100);glMatrixMode(GL_MODELVIEW);glLoadIdentity();glClearColor(12/255.0f,16/255.0f,20/255.0f,1);glClear(GL_COLOR_BUFFER_BIT);
        avzh::Renderer renderer;std::ifstream glyph_file(argv[2],std::ios::binary);std::string bytes((std::istreambuf_iterator<char>(glyph_file)),{});require(bytes.size()%2==0 && !bytes.empty(),"Glyph inventory unavailable");std::wstring glyphs(bytes.size()/2,L'\0');memcpy(&glyphs[0],bytes.data(),bytes.size());require(renderer.glyphs(glyphs),"Selected GDI font lacks an approved character");
        auto* memory=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x300000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));require(memory!=nullptr,"Fixture allocation failed");
        unsigned char text_code[]={0x55,0x8b,0xec,0x81,0xec,0x40,0x08,0,0,0xb8,42,0,0,0,0x8b,0xe5,0x5d,0xc3};unsigned char measure_code[]={0x55,0x8b,0xec,0x81,0xec,0x14,0x04,0,0,0xb8,42,0,0,0,0x8b,0xe5,0x5d,0xc3};memcpy(memory+0x6e080,text_code,sizeof(text_code));memcpy(memory+0x6df00,measure_code,sizeof(measure_code));
        unsigned char name_code[]={0xc7,0x01,'T','e','s','t',0xc7,0x41,0x04,'H','e','r','o',0xc6,0x41,0x08,0,0xc3};memcpy(memory+0x6ede0,name_code,sizeof(name_code));
        FixtureInitialize(memory,argv[1],output.c_str());
        require(FixtureNameExpansion(),"ECX player-name expansion ABI or placeholder binding failed");
        require(call_text(memory+0x6e080,"AVZH_COMPLETELY_UNMATCHED_371",0)==42,"Unknown text did not reach original trampoline");require(call_measure(memory+0x6df00,"AVZH_COMPLETELY_UNMATCHED_371")==42,"Unknown measurement did not reach original trampoline");
        GLuint sentinel=0;glGenTextures(1,&sentinel);glBindTexture(GL_TEXTURE_2D,sentinel);glColor4f(.2f,.3f,.4f,.5f);glEnable(GL_DEPTH_TEST);glEnable(GL_SCISSOR_TEST);glScissor(3,4,17,19);
        call_text(memory+0x6e080,"Blademaster",1);require(*reinterpret_cast<short*>(memory+0x2bef1c)==17,"Successful text entry did not update native line-height state");
        GLint binding=0,scissor[4]{};GLfloat color[4]{};glGetIntegerv(GL_TEXTURE_BINDING_2D,&binding);glGetIntegerv(GL_SCISSOR_BOX,scissor);glGetFloatv(GL_CURRENT_COLOR,color);
        require(static_cast<GLuint>(binding)==sentinel && glIsEnabled(GL_DEPTH_TEST) && glIsEnabled(GL_SCISSOR_TEST),"OpenGL state leaked");require(scissor[0]==3 && scissor[1]==4 && scissor[2]==17 && scissor[3]==19 && std::abs(color[0]-.2f)<.001f && std::abs(color[3]-.5f)<.001f,"Clip/color state leaked");
        require(call_measure(memory+0x6df00,"Blademaster")>0,"Translated measurement failed");
        call_text(memory+0x6e080,"Your Coins: 321",0);
        glDisable(GL_SCISSOR_TEST);glClear(GL_COLOR_BUFFER_BIT);glEnable(GL_SCISSOR_TEST);
        *reinterpret_cast<short*>(memory+0x2043ec)=10;*reinterpret_cast<short*>(memory+0x2043ee)=10;*reinterpret_cast<short*>(memory+0x2043f0)=110;*reinterpret_cast<short*>(memory+0x2043f2)=280;
        call_text(memory+0x6e080,quoted,0);require(*reinterpret_cast<short*>(memory+0x2bef1c)>=34,"CJK dialogue did not wrap into multiple native-height lines");
        glFinish();require(glGetError()==GL_NO_ERROR,"OpenGL reported a rendering error");
        std::vector<unsigned char> pixels(320*160*4);glReadPixels(0,0,320,160,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());size_t changed=0;for(int y=0;y<160;++y)for(int x=0;x<320;++x){size_t i=(y*320+x)*4;if(pixels[i]>40 || pixels[i+1]>40 || pixels[i+2]>40)++changed;if(x<10 || x>=280 || 159-y<10 || 159-y>=110)require(std::abs(static_cast<int>(pixels[i])-12)<=2 && std::abs(static_cast<int>(pixels[i+1])-16)<=2 && std::abs(static_cast<int>(pixels[i+2])-20)<=2,"Text escaped native clip rectangle");}require(changed>50,"No visible CJK glyphs in offscreen output");
        std::ofstream picture((output+L"\\cjk_render.ppm").c_str(),std::ios::binary);picture<<"P6\n320 160\n255\n";for(int y=159;y>=0;--y)for(int x=0;x<320;++x)picture.write(reinterpret_cast<char*>(&pixels[(y*320+x)*4]),3);picture.close();
        FixtureFinish();VirtualFree(memory,0,MEM_RELEASE);glDeleteTextures(1,&sentinel);wglMakeCurrent(nullptr,nullptr);wglDeleteContext(context);SelectObject(dc,old);DeleteObject(dib);DeleteDC(dc);FreeLibrary(proxy);
        std::ofstream report((output+L"\\report.json").c_str(),std::ios::binary);report<<"{\n  \"status\":\"passed\",\n  \"dictionary_keys\":"<<dictionary.size()<<",\n  \"format_patterns\":"<<dictionary.patterns()<<",\n  \"glyphs_checked\":"<<glyphs.size()<<",\n  \"exports_checked\":"<<AVZH_FORWARD_COUNT<<",\n  \"visible_text_pixels\":"<<changed<<",\n  \"x86_abi_stack_and_registers\":true,\n  \"unknown_text_trampoline\":true,\n  \"gl_state_preserved\":true,\n  \"player_name_placeholder\":true,\n  \"script_quotes_and_heading_markers\":true,\n  \"cjk_wrapping_and_clip\":true,\n  \"offscreen_gdi_gl\":true,\n  \"game_started\":false,\n  \"in_game_verified\":false\n}\n";std::cout<<"Component tests passed; no game launched.\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 1;}
}
