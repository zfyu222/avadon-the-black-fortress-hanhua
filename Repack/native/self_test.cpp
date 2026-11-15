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
#include "camera_follow.hpp"
#include "forward_metadata.hpp"

extern "C" void FixtureInitialize(void*,const wchar_t*,const wchar_t*);
extern "C" void FixtureFinish();
extern "C" bool FixtureNameExpansion();
extern "C" void FixtureFontScale(int);
extern "C" void FixtureCameraEnable();
extern "C" void FixtureMovementSpeed(unsigned);
extern "C" void FixtureMovementEnable();
extern "C" void FixtureInventoryEnable();
extern "C" void FixtureInteractionEnable();
extern "C" void FixtureInteractionMode(unsigned);
extern "C" void FixtureKeyModifiers(int);
static void require(bool test,const char* reason){if(!test)throw std::runtime_error(reason);}

static void call_walk(void* entry,void* position){
    int before_stack=0,after_stack=0;
    __asm {
        mov before_stack,esp
        mov esi,position
        movzx eax,word ptr[esi+0x12]
        mov edx,entry
        call edx
        mov after_stack,esp
    }
    require(before_stack==after_stack,"Walking hook did not preserve RET 8 cleanup");
}
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
        std::string a,b,joined;
        require(dictionary.lookup("Fatigue: 1. ",a) && dictionary.lookup("Turns to recover: 6. ",b),"Approved numeric messages missing");
        require(dictionary.lookup("Fatigue: 1. Turns to recover: 6. ",joined) && joined==a+b,"Complete message composition failed");
        require(dictionary.lookup("Weight: 4 lbs.",a) && dictionary.lookup(" Weight: 4 lbs.",b) && b==" "+a,"UI padding adaptation failed");
        require(dictionary.lookup("Shortcut: ",a) && dictionary.lookup("Shortcut: w",b) && b==a+"w","Shortcut label binding failed");
        require(dictionary.lookup("Health: ",a) && dictionary.lookup("Health: 64/65",b) && b==a+"64/65","Fractional label binding failed");
        require(dictionary.lookup("Instructions",a) && dictionary.lookup("Instructions (F1)",b) && b==a+" (F1)","Hotkey label binding failed");
        require(!dictionary.lookup("Fatigue: 1. Unapproved trailing prose.",value),"Partial numeric composition must fall back");
        require(!dictionary.lookup("Shortcut: unapproved prose",value),"Unapproved label prose must fall back");
        require(!dictionary.lookup("Instructions (unapproved prose)",value),"Unapproved parenthetical must fall back");
        require(dictionary.lookup("Starting new round.",a) && dictionary.lookup("Starting new round."+std::string(60,' '),b) && b==a+std::string(60,' '),"Fixed-width console padding failed");
        const char* actions[]={"Use Ability","Train Character/See Stats","Inventory","Get Item","Journal","Start Combat","End Combat","Instructions","Switch Default Weapon","Quick Save","Quick Load","Wait","Select Char 1","Select Key C","Show/Hide Text Console"};
        const char* keys[]={"a","Shift+/","i","g","No Shortcut","f","f","F1","w","F3","F4","Space","1","c","t"};
        for(int i=0;i<15;++i){require(dictionary.lookup(actions[i],a),"Approved key action absent");std::string key=keys[i],expected=key;if(key=="No Shortcut")require(dictionary.lookup(key,expected),"Approved empty-key value absent");require(dictionary.lookup(std::string(actions[i])+" - "+key,b) && b==a+" - "+expected,"Key-binding composition failed");}
        unsigned binding_tests=15;
        for(int i=1;i<=4;++i)for(int item=0;item<2;++item){std::string action=std::string(item?"Quick Use Item ":"Quick Spell ")+std::to_string(i),key="F"+std::to_string(i+(item?8:4));require(dictionary.lookup(action,a) && dictionary.lookup(action+" - "+key,b) && b==a+" - "+key,"Numbered quick binding failed");++binding_tests;}
        for(int i=2;i<=5;++i){std::string action="Select Char "+std::to_string(i),key=std::to_string(i);require(dictionary.lookup(action,a) && dictionary.lookup(action+" - "+key,b) && b==a+" - "+key,"Character binding failed");++binding_tests;}
        for(char letter='A';letter<='X';++letter){if(letter=='C')continue;std::string action="Select Key "+std::string(1,letter),key(1,letter-'A'+'a');require(dictionary.lookup(action,a) && dictionary.lookup(action+" - "+key,b) && b==a+" - "+key,"Alphabet binding failed");++binding_tests;}
        const char* console_cases[]={"Starting new round.","A quest has been completed.","A new quest has been added to your list.","  (To see your quest list, press the Journal button.)","Now active: Tristram.","Ending Combat Mode","Save: Game saved.","Load: Game loaded.","Experimental Wolf takes 19 points of damage.","Experimental Wolf uses ability: Bite.","Tristram uses ability: Melee Attack.","Experimental Wolf takes 11 points of physical damage. (0 blocked.)","Combat has begun! (To end combat, press the Peace button below.)"};
        for(auto input:console_cases){if(!dictionary.lookup(input,a))throw std::runtime_error(std::string("Reported console message failed: ")+input);require(dictionary.lookup(std::string(input)+std::string(60,' '),b) && b==a+std::string(60,' '),"Reported padded console message failed");}
        std::string door="Open Door: The door is locked, and you don't have enough lockpicks to get it open. (You need ";
        require(dictionary.lookup(door,a) && dictionary.lookup(door+"12.)",b) && b==a+"12.)","Numeric script fragment failed");
        std::string approved_name;require(dictionary.lookup("Tristram",approved_name) && dictionary.lookup("Now active: ",a) && dictionary.lookup("Now active: Tristram.",b) && b==a+approved_name+'.',"Approved character-name field failed");
        require(dictionary.lookup("Now active: ZyxHero.",b) && b==a+"ZyxHero.","Opaque player-name field failed");
        require(!dictionary.lookup(door+"unknown prose.)",value),"Unapproved prose must not complete a numeric fragment");
        require(!dictionary.lookup("Inventory - arbitrary prose",value),"Non-key suffix must not be accepted");
        std::ofstream console_report((output+L"\\console_binding_report.json").c_str(),std::ios::binary);console_report<<"{\"status\":\"passed\",\"padding\":true,\"bindings\":"<<binding_tests<<",\"console_cases\":13,\"numeric_script_fragment\":true,\"name_label\":true,\"unknown_prose_falls_back\":true,\"game_started\":false}\n";console_report.close();
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
        int ink=renderer.ink_height(L'汉',13);require(ink>=10 && ink<=13,"CJK body glyph too small or too tall");
        std::ofstream dynamic_report((output+L"\\dynamic_font_report.json").c_str(),std::ios::binary);dynamic_report<<"{\"status\":\"passed\",\"complete_message_composition\":true,\"padding_and_shortcut_labels\":true,\"partial_prose_falls_back\":true,\"cjk_body_ink_height\":"<<ink<<",\"native_line_step\":13,\"game_started\":false}\n";dynamic_report.close();
        auto* memory=static_cast<unsigned char*>(VirtualAlloc(nullptr,0xc00000,MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE));require(memory!=nullptr,"Fixture allocation failed");
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
        const std::wstring ini=output+L"\\font_test.ini";
        require(avzh::FontSettings::load(ini).percent==100,"Missing font config must preserve baseline");
        WritePrivateProfileStringW(L"Font",L"ScalePercent",L"150",ini.c_str());
        auto large=avzh::FontSettings::load(ini);require(large.percent==150 && large.step(12)==19 && large.step(16)==25,"150 percent config incorrect");
        WritePrivateProfileStringW(L"Font",L"ScalePercent",L"9999",ini.c_str());require(avzh::FontSettings::load(ini).percent==200,"Upper font bound failed");
        WritePrivateProfileStringW(L"Font",L"ScalePercent",L"-20",ini.c_str());require(avzh::FontSettings::load(ini).percent==100,"Lower font bound failed");
        DeleteFileW(ini.c_str());
        require(renderer.ink_height(L'汉',19)>ink,"150 percent glyph ink did not grow");
        avzh::TextState fitted;fitted.align=1;fitted.font=12;fitted.right=110;fitted.bottom=22;fitted.settings=large;
        int fitted_step=renderer.layout_step(L"设置",fitted);require(fitted_step==18,"Fixed label height fit failed");
        fitted.right=35;fitted.bottom=60;int width_step=renderer.layout_step(L"设置",fitted);
        require(width_step>=13 && width_step<19 && renderer.measure(L"设置",width_step)<=29,"Fixed label width fit failed");
        fitted.settings.fit_labels=false;require(renderer.layout_step(L"设置",fitted)==19,"Fit toggle ignored");
        FixtureFontScale(150);std::string measured;require(dictionary.lookup("Blademaster",measured),"Missing scaled width fixture");
        require(call_measure(memory+0x6df00,"Blademaster")==renderer.measure(avzh::utf8(measured),19),"Hook width does not use configured scale");
        call_text(memory+0x6e080,"Blademaster",1);require(*reinterpret_cast<short*>(memory+0x2bef1c)==25,"Hook did not return enlarged line step");
        require(call_measure(memory+0x6df00,"AVZH_COMPLETELY_UNMATCHED_371")==42,"Scaled unknown width must fall back");
        FixtureFontScale(100);
        int baseline_lines=0,large_lines=0;
        for(int percent:{100,150}){
            glDisable(GL_SCISSOR_TEST);glClear(GL_COLOR_BUFFER_BIT);
            avzh::TextState preview;preview.font=12;preview.left=10;preview.top=10;preview.right=310;preview.bottom=150;preview.screen_width=320;preview.screen_height=160;
            preview.clip_left=10;preview.clip_top=10;preview.clip_right=310;preview.clip_bottom=150;preview.settings.percent=percent;
            auto rendered=renderer.draw(L"你很快就会明白，在阿瓦登，你只能知道那些你必须知道的事情。这是为了保护你，也是为了保护我们。|任务日志与物品说明会按新的字号重新换行。",preview);
            if(percent==100)baseline_lines=rendered.height/13;else large_lines=rendered.height/19;
            glFinish();require(glGetError()==GL_NO_ERROR,"Scaled drawing GL error");glReadPixels(0,0,320,160,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
            for(int y=0;y<160;++y)for(int x=0;x<320;++x)if(x<10 || x>=310 || 159-y<10 || 159-y>=150){size_t i=(y*320+x)*4;require(std::abs(static_cast<int>(pixels[i])-12)<=2,"Scaled text escaped clipping");}
            std::ofstream scaled_picture((output+L"\\font_"+std::to_wstring(percent)+L".ppm").c_str(),std::ios::binary);scaled_picture<<"P6\n320 160\n255\n";for(int y=159;y>=0;--y)for(int x=0;x<320;++x)scaled_picture.write(reinterpret_cast<char*>(&pixels[(y*320+x)*4]),3);
        }
        require(large_lines>baseline_lines,"Enlarged paragraph did not reflow");
        std::ofstream scale_report((output+L"\\font_scale_report.json").c_str(),std::ios::binary);
        scale_report<<"{\"status\":\"passed\",\"scale_percent\":150,\"body_step_before\":13,\"body_step_after\":19,\"body_ink_before\":"<<ink<<",\"body_ink_after\":"<<renderer.ink_height(L'汉',19)<<",\"baseline_lines\":"<<baseline_lines<<",\"enlarged_lines\":"<<large_lines<<",\"fixed_label_height_and_width_fit\":true,\"hook_measure_and_line_step\":true,\"scaled_clipping\":true,\"config_bounds_and_missing_default\":true,\"game_started\":false}\n";
        avzh::CameraFollow follow;avzh::CameraFrame frame;frame.allowed=true;frame.mode=10;frame.preferred=0;
        frame.actors[0]={true,1000,1200,0};
        require(!follow.update(frame).follow,"Camera snapped on initial observation");
        frame.tick=32;require(!follow.update(frame).follow,"Idle camera must remain free");
        frame.actors[0].motion=2;frame.actors[0].x+=8;frame.tick=64;
        auto target=follow.update(frame);require(target.follow && target.x==1008 && target.y==1200,"Walking failed to reacquire camera");
        frame.tick=96;require(follow.update(frame).follow,"Camera lost walking actor between simulation steps");
        frame.actors[0].motion=0;require(!follow.update(frame).follow,"Stopped actor did not release edge scrolling");
        frame.actors[0].motion=2;frame.actors[0].y+=8;frame.tick=128;require(follow.update(frame).follow,"Resume after free pan failed");
        frame.allowed=false;require(!follow.update(frame).follow,"Blocked or menu camera followed");
        frame.allowed=true;frame.actors[0].x+=8;require(!follow.update(frame).follow,"Returning from modal snapped camera");
        frame.actors[0].x+=8;frame.tick=160;require(follow.update(frame).follow,"Walking after modal failed");
        frame.actors[0].x+=4096;frame.tick=192;require(!follow.update(frame).follow,"Teleport mistaken for walking");
        frame.layer=1;frame.actors[0].x+=8;require(!follow.update(frame).follow,"Floor transition caused stale follow");
        frame.mode=15;frame.preferred=9;require(!follow.update(frame).follow,"Enemy turn took camera");
        frame.actors[0].x+=8;frame.tick=224;require(!follow.update(frame).follow,"Party movement during enemy turn took camera");
        frame.preferred=0;frame.actors[0].x+=8;frame.tick=256;require(!follow.update(frame).follow,"Returning to character 1 turn snapped view");
        frame.actors[0].x+=8;frame.tick=288;require(follow.update(frame).follow,"Character 1 combat movement not followed");
        frame.tick=512;require(!follow.update(frame).follow,"Stalled path kept camera locked");
        frame.actors[0].valid=false;require(!follow.update(frame).follow,"Invalid actor followed");
        follow.reset();frame=avzh::CameraFrame{};frame.allowed=true;frame.mode=10;frame.preferred=1;
        frame.actors[0]={true,1000,1200,0};
        for(int id=1;id<8;++id)frame.actors[id]={true,2000+id*10,2400,2};
        follow.update(frame);
        for(int id=1;id<8;++id){frame.actors[id].x+=8;frame.tick+=32;require(!follow.update(frame).follow,"Companion movement acquired camera");}
        frame.actors[0].motion=2;frame.actors[0].x+=8;frame.tick+=32;
        auto primary=follow.update(frame);require(primary.follow && primary.actor==0,"Selection displaced character 1 camera ownership");
        frame.actors[1].x+=8;frame.actors[0].motion=0;frame.tick+=32;require(!follow.update(frame).follow,"Companion kept follow after character 1 stopped");
        frame.actors[0].valid=false;frame.actors[1].x+=8;auto fallback=follow.update(frame);require(fallback.follow && fallback.actor==1,"Absent character 1 did not fall back to character 2");
        frame.actors[1].motion=0;require(!follow.update(frame).follow,"Stopped character 2 did not release camera");
        frame.mode=15;frame.preferred=1;frame.actors[1].motion=2;follow.update(frame);
        frame.actors[1].x+=8;require(follow.update(frame).actor==1,"Character 2 combat turn not followed while character 1 is absent");
        frame.actors[1].valid=false;frame.actors[2].x+=8;require(!follow.update(frame).follow,"Character 3 took over when both targets were absent");
        frame.actors[1].valid=true;
        frame.mode=15;frame.preferred=1;frame.actors[0].valid=true;frame.actors[0].motion=2;frame.actors[0].x+=8;require(!follow.update(frame).follow,"Companion combat turn acquired camera");
        auto projection=avzh::camera_position(1000,1200);require(projection.screen_x==-46 && projection.screen_y==343,"Native camera projection differs");
        auto clamped=avzh::camera_position(-1000,50000);require(clamped.x==-512 && clamped.y==33280,"Camera bounds invalid");
        // Real hook/trampoline against synthetic code and memory, never game code.
        const unsigned char camera_code[]={0x55,0x8b,0xec,0x83,0xec,0x5c,0xb8,42,0,0,0,0x8b,0xe5,0x5d,0xc3};
        memcpy(memory+0x32970,camera_code,sizeof(camera_code));
        auto native_short=[&](uintptr_t va)->short&{return *reinterpret_cast<short*>(memory+va-0x400000);};
        auto native_int=[&](uintptr_t va)->int&{return *reinterpret_cast<int*>(memory+va-0x400000);};
        native_short(0x6bed48)=10;native_short(0x6bed4c)=0;native_short(0x73b90c)=0;native_short(0x5cf394)=0;
        *reinterpret_cast<HWND*>(memory+0x6bed20-0x400000)=GetForegroundWindow();
        native_short(0x74236a)=1;native_short(0x742386)=2;native_short(0x7427d4)=1;native_short(0x742398)=0;
        native_int(0x742388)=1000;native_int(0x74238c)=1200;native_short(0x7438e2)=2;
        native_int(0xeb84b8)=5000;native_int(0xeb84bc)=6000;
        FixtureCameraEnable();require(call_text(memory+0x32970,"",0)==42,"Camera trampoline or ABI broken");
        require(native_int(0xeb84b8)==5000,"Initial hook observation changed camera");
        native_int(0x742388)=1008;native_int(0x6beeb8)=32;call_text(memory+0x32970,"",0);
        require(native_int(0xeb84b8)==1008 && native_int(0xeb84bc)==1200 && native_int(0xeb84c0)==-45 && native_int(0xeb84c4)==345,"Hook camera world/projected coordinates inconsistent");
        native_short(0x7438e2)=0;native_int(0xeb84b8)=9000;call_text(memory+0x32970,"",0);require(native_int(0xeb84b8)==9000,"Idle hook blocked native panning");
        native_short(0x6bed4c)=0x27;native_short(0x7438e2)=2;native_int(0x742388)+=8;call_text(memory+0x32970,"",0);require(native_int(0xeb84b8)==9000,"Menu hook overwrote view");
        std::ofstream camera_report((output+L"\\camera_report.json").c_str(),std::ios::binary);
        camera_report<<"{\"status\":\"passed\",\"character_1_priority\":true,\"companions_excluded_while_primary_present\":true,\"selection_does_not_change_target\":true,\"absent_primary_falls_back_to_character_2\":true,\"companion_combat_turn_excluded\":true,\"walking_reacquires\":true,\"idle_preserves_native_pan\":true,\"stopped_releases\":true,\"simulation_gap_grace\":true,\"modal_and_floor_reset\":true,\"enemy_turn_excluded\":true,\"teleport_excluded\":true,\"stalled_path_releases\":true,\"world_projection_and_bounds\":true,\"x86_camera_hook_trampoline_and_registers\":true,\"native_memory_integration\":true,\"game_started\":false,\"in_game_verified\":false}\n";
        // Synthetic native vector stores AX as nominal speed and X step.
        const unsigned char vector_code[]={0x55,0x8b,0xec,0x83,0xec,0x08,0x66,0x89,0x46,0x12,0x66,0x89,0x46,0x14,0x8b,0xe5,0x5d,0xc2,0x08,0x00};
        const unsigned char walk_call[]={0x6a,0,0x6a,0,0xe8,0x86,0xfd,0,0,0xc3};
        memcpy(memory+0x51390,vector_code,sizeof(vector_code));
        memcpy(memory+0x41601,walk_call,sizeof(walk_call));
        FixtureMovementEnable();
        auto walk=[&](uintptr_t actor){
            auto position=memory+actor-0x400000+0x20;
            auto entry=memory+0x41601;
            call_walk(entry,position);
            return native_short(actor+0x34);
        };
        constexpr uintptr_t hero=0x742368,second=hero+0x19ac;
        native_short(0x6bed48)=10;native_short(0x6bed4c)=0;
        native_short(hero+0x32)=24;native_short(second+0x32)=24;
        native_short(second+0x1e)=2;
        FixtureMovementSpeed(100);require(walk(hero)==24,"100 percent changed native speed");
        FixtureMovementSpeed(137);require(walk(hero)==33,"Custom percent was not applied");
        FixtureMovementSpeed(200);require(walk(hero)==48 && walk(hero)==48 && native_short(hero+0x32)==24,"200 percent compounded the nominal speed");
        require(walk(second)==48 && walk(second)==48 && native_short(second+0x32)==24,
            "Companion did not get the same multiplier or its speed compounded");
        constexpr uintptr_t last=hero+7*0x19ac,npc=last+0x19ac;
        for(uintptr_t actor:{last,npc}){
            native_short(actor+0x1e)=2;
            native_short(actor+0x32)=20;
        }
        require(walk(last)==40,"Last party slot was not accelerated");
        require(walk(npc)==20,"Actor outside party slots was accelerated");
        native_short(last+0x30)=1;
        require(walk(last)==20,"Companion on another layer was accelerated");
        native_short(last+0x30)=0;
        native_short(last+0x1e)=0;
        require(walk(last)==20,"Absent companion was accelerated");
        native_short(hero+0x1e)=0;
        require(walk(second)==48,"Second character did not receive speed while hero absent");
        native_short(0x6bed48)=15;require(walk(second)==24,"Combat was accelerated");
        native_short(0x6bed48)=10;native_short(0x6bed4c)=10;require(walk(second)==24,"Menu movement was accelerated");
        std::ofstream speed_report((output+L"\\movement_report.json").c_str(),std::ios::binary);
        speed_report<<"{\"status\":\"passed\",\"percentages\":[100,137,200],\"no_compounding\":true,\"all_active_party_slots_scaled\":true,\"non_party_and_absent_actors_excluded\":true,\"combat_and_menu_excluded\":true,\"ret8_cleanup\":true,\"in_game_verified\":false}\n";
        const unsigned char labels_code[]={0x55,0x8b,0xec,0x83,0xec,0x1c,0xb8,42,0,0,0,0x8b,0xe5,0x5d,0xc3};
        const unsigned char sight_code[]={0x31,0xc0,0xc3};
        unsigned char rectangle_code[]={0xb8,0,0,0,0,0xff,0x00,0xc3};
        int rectangles=0;
        const auto counter=reinterpret_cast<uintptr_t>(&rectangles);
        memcpy(rectangle_code+1,&counter,4);
        memcpy(memory+0x350c0,labels_code,sizeof(labels_code));
        memcpy(memory+0xa900,sight_code,sizeof(sight_code));
        memcpy(memory+0x76c0,rectangle_code,sizeof(rectangle_code));
        FixtureInteractionEnable();
        native_short(0x6bed48)=10;native_short(0x6bed4c)=0;
        native_short(0x6043ec)=0;native_short(0x6043ee)=0;native_short(0x6043f0)=160;native_short(0x6043f2)=320;
        native_short(0x6043fc)=0;native_short(0x6043fe)=0;native_short(0x604400)=160;native_short(0x604402)=320;
        native_int(0x6af7f8)=9000;
        native_short(0x8b33f2)=1;native_short(0x714958+0x58)=10;
        native_short(0x8b3428)=40;native_short(0x8b342a)=50;native_short(0x8b342c)=80;native_short(0x8b342e)=90;
        auto& shift=memory[0x6bee3b-0x400000];
        auto& tile_visible=memory[0x661cc8-0x400000];
        tile_visible=1;
        auto draw_labels=[&](){
            rectangles=0;
            require(call_text(memory+0x350c0,"",0)==42,"Labels trampoline changed");
            return rectangles;
        };
        require(draw_labels()==0,"Marker shown with Shift released");
        FixtureInteractionMode(2);require(draw_labels()==4,"Always mode requires Shift");
        FixtureInteractionMode(0);shift=1;require(draw_labels()==0,"Disabled mode draws markers");
        FixtureInteractionMode(1);
        shift=1;require(draw_labels()==4,"Interactive object did not receive exactly one marker");
        native_short(0x714958+0x58)=9;require(draw_labels()==0,"Decoration marked");
        native_short(0x714958+0x58)=19;require(draw_labels()==4,"Last interactive type omitted");
        native_short(0x8b33f4)=1;require(draw_labels()==0,"Inactive object marked");
        native_short(0x8b33f4)=0;tile_visible=0;native_int(0x6af7f8)=-1;
        require(draw_labels()==4,"On-screen object outside party sight and absent from the draw list was omitted");
        native_short(0x8b340c)=1;require(draw_labels()==0,"Other layer marked");
        native_short(0x8b340c)=0;native_short(0x8b342a)=340;native_short(0x8b342e)=360;
        require(draw_labels()==0,"Off-screen object marked");
        native_short(0x8b342a)=50;native_short(0x8b342e)=90;
        native_short(0x6bed4c)=10;require(draw_labels()==0,"Inventory overlay marked");
        native_short(0x6bed4c)=0;shift=0;require(draw_labels()==0,"Marker did not disappear on release");
        std::ofstream interaction_report((output+L"\\interaction_report.json").c_str(),std::ios::binary);
        interaction_report<<"{\"status\":\"passed\",\"shift_hold_release\":true,\"always_and_disabled_modes\":true,\"native_labels_trampoline\":true,\"native_interactive_type_filter\":true,\"inactive_and_offscreen_excluded\":true,\"on_screen_outside_party_sight_and_draw_list_marked\":true,\"in_game_verified\":false}\n";
        const unsigned char keyboard_code[]={0x55,0x8b,0xec,0x83,0xe4,0xf8,0x83,0xec,0x0c,0x8b,0x45,0x08,0x8b,0xe5,0x5d,0xc3};
        memcpy(memory+0x67370,keyboard_code,sizeof(keyboard_code));FixtureInventoryEnable();
        auto key_event=[&](int key){return call_text(memory+0x67370,reinterpret_cast<const char*>(key),0);};
        native_short(0x6bed48)=10;native_short(0x6bed4c)=10;
        native_short(0x60444e)=0x49;native_short(0x6044ee)=0;
        require(key_event(0x49)==0x18,"Inventory key did not route to native Escape");
        require(key_event(0x4a)==0x4a,"Unrelated inventory item key changed");
        native_short(0x6bed4c)=0;require(key_event(0x49)==0x49,"Inventory opening path changed");
        native_short(0x6bed4c)=0x21;require(key_event(0x49)==0x49,"Shortcut editor input intercepted");
        native_short(0x6bed4c)=10;native_short(0x6bed48)=0;require(key_event(0x49)==0x49,"Main menu input intercepted");
        native_short(0x6bed48)=15;require(key_event(0x49)==0x18,"Combat inventory toggle failed");
        native_short(0x60444e)=0x4a;require(key_event(0x49)==0x49 && key_event(0x4a)==0x18,"Live custom key change was not respected");
        for(int modifier=1;modifier<=3;++modifier){
            native_short(0x6044ee)=static_cast<short>(modifier);FixtureKeyModifiers(0);require(key_event(0x4a)==0x4a,"Wrong modifiers closed inventory");
            FixtureKeyModifiers(modifier);require(key_event(0x4a)==0x18,"Custom modifier not passed to native matcher");
        }
        native_short(0x6044ee)=0;FixtureKeyModifiers(0);
        for(uintptr_t flag:{0x6bee47,0x6b1cdd,0x6b1cdf}){
            *reinterpret_cast<unsigned char*>(memory+flag-0x400000)=1;require(key_event(0x4a)==0x4a,"Native input capture or pending action bypassed");
            *reinterpret_cast<unsigned char*>(memory+flag-0x400000)=0;
        }
        native_short(0x60444e)=0;require(key_event(0x4a)==0x4a,"Unassigned inventory key intercepted input");
        native_short(0x60444e)=0x4a;require(key_event(0x18)==0x18,"Original Escape changed");
        std::ofstream inventory_report((output+L"\\inventory_report.json").c_str(),std::ios::binary);
        inventory_report<<"{\"status\":\"passed\",\"open_path_unchanged\":true,\"inventory_hotkey_routes_native_escape\":true,\"live_custom_key\":true,\"all_three_modifier_modes\":true,\"wrong_modifiers_and_unassigned_ignored\":true,\"other_menus_and_captured_input_unchanged\":true,\"combat_inventory\":true,\"unrelated_item_keys_unchanged\":true,\"keyboard_hook_stack_registers\":true,\"synthetic_native_matcher_dx_and_stack_abi\":true,\"native_held_item_and_close_policy\":\"delegated_to_original_escape_path_static_evidence\",\"game_started\":false,\"in_game_verified\":false}\n";
        FixtureFinish();VirtualFree(memory,0,MEM_RELEASE);glDeleteTextures(1,&sentinel);wglMakeCurrent(nullptr,nullptr);wglDeleteContext(context);SelectObject(dc,old);DeleteObject(dib);DeleteDC(dc);FreeLibrary(proxy);
        std::ofstream report((output+L"\\report.json").c_str(),std::ios::binary);report<<"{\n  \"status\":\"passed\",\n  \"dictionary_keys\":"<<dictionary.size()<<",\n  \"format_patterns\":"<<dictionary.patterns()<<",\n  \"glyphs_checked\":"<<glyphs.size()<<",\n  \"exports_checked\":"<<AVZH_FORWARD_COUNT<<",\n  \"visible_text_pixels\":"<<changed<<",\n  \"x86_abi_stack_and_registers\":true,\n  \"unknown_text_trampoline\":true,\n  \"gl_state_preserved\":true,\n  \"player_name_placeholder\":true,\n  \"script_quotes_and_heading_markers\":true,\n  \"cjk_wrapping_and_clip\":true,\n  \"offscreen_gdi_gl\":true,\n  \"game_started\":false,\n  \"in_game_verified\":false\n}\n";std::cout<<"Component tests passed; no game launched.\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 1;}
}
