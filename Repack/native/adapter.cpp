#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <array>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <set>
#include <sstream>
#include "renderer.hpp"
#include "camera_follow.hpp"
#include "forward_metadata.hpp"
#include "MinHook.h"

#pragma comment(lib,"bcrypt.lib")
#pragma comment(lib,"gdi32.lib")
#pragma comment(lib,"user32.lib")
#pragma comment(lib,"opengl32.lib")

extern "C" { FARPROC g_forwards[AVZH_FORWARD_COUNT]{};void* g_original_text=nullptr;void* g_original_measure=nullptr;void* g_original_camera=nullptr;void* g_original_keyboard=nullptr;void* g_original_walk_vector=nullptr;void* g_original_world_labels=nullptr; }
namespace {
HMODULE module_handle=nullptr,real_winmm=nullptr;
INIT_ONCE real_once=INIT_ONCE_STATIC_INIT,adapter_once=INIT_ONCE_STATIC_INIT;
uintptr_t game_base=0;bool enabled=false;
std::wstring data_path;
avzh::Dictionary dictionary;
avzh::FontSettings font_settings;
bool camera_enabled=false;
bool interaction_markers_enabled=false;
unsigned movement_percent=100;
bool inventory_toggle_enabled=false;
avzh::CameraFollow camera_follow;
thread_local avzh::Renderer renderer;
std::mutex log_mutex;std::set<std::string> unmatched;

void log(const std::string& message) noexcept {
    try{std::lock_guard<std::mutex> guard(log_mutex);if(data_path.empty())return;std::ofstream file((data_path+L"\\runtime.log").c_str(),std::ios::app|std::ios::binary);file<<message<<"\r\n";}catch(...){}
}
template<class T>T& at(uintptr_t address){return *reinterpret_cast<T*>(game_base+address-0x400000);}
bool file_exists(const std::wstring& path){return GetFileAttributesW(path.c_str())!=INVALID_FILE_ATTRIBUTES;}
std::string executable_hash(const std::wstring& path){
    BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;DWORD object_size=0,result_size=0;
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("SHA256 provider unavailable");
    if(BCryptGetProperty(algorithm,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&object_size),sizeof(object_size),&result_size,0)<0){BCryptCloseAlgorithmProvider(algorithm,0);throw std::runtime_error("SHA256 metadata unavailable");}
    std::vector<unsigned char> object(object_size);std::array<unsigned char,32> digest{};
    if(BCryptCreateHash(algorithm,&hash,object.data(),object_size,nullptr,0,0)<0){BCryptCloseAlgorithmProvider(algorithm,0);throw std::runtime_error("Cannot initialize SHA256");}
    std::ifstream file(path.c_str(),std::ios::binary);std::array<char,65536> bytes{};bool valid=static_cast<bool>(file);
    while(file){file.read(bytes.data(),bytes.size());auto count=file.gcount();if(count && BCryptHashData(hash,reinterpret_cast<PUCHAR>(bytes.data()),static_cast<ULONG>(count),0)<0){valid=false;break;}}
    if(BCryptFinishHash(hash,digest.data(),static_cast<ULONG>(digest.size()),0)<0)valid=false;
    BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(algorithm,0);if(!valid)throw std::runtime_error("Cannot hash executable");
    std::ostringstream text;text<<std::hex<<std::setfill('0');for(auto b:digest)text<<std::setw(2)<<static_cast<unsigned>(b);return text.str();
}
std::string active_name(){
    char name[1024]="[N]";using Expand=void(__fastcall*)(char*);reinterpret_cast<Expand>(game_base+0x6ede0)(name);return name;
}
std::wstring localized(const char* source,bool& found){
    found=false;if(!source)return {};size_t length=strnlen(source,4097);if(length>4096)return {};
    std::string original(source,length),target;if(!dictionary.lookup(original,target)){
        std::lock_guard<std::mutex> guard(log_mutex);if(unmatched.size()<1000 && unmatched.insert(original).second){std::ofstream file((data_path+L"\\unmatched.txt").c_str(),std::ios::app|std::ios::binary);file.write(original.data(),original.size());file<<"\r\n";}return {};
    }
    if(target==original)return {};
    // [N] is expanded only after dictionary matching, just as the native route.
    if(target.find("[N]")!=std::string::npos){std::string name=active_name();int count=MultiByteToWideChar(1252,0,name.data(),static_cast<int>(name.size()),nullptr,0);std::wstring wide(count,L'\0');if(count)MultiByteToWideChar(1252,0,name.data(),static_cast<int>(name.size()),&wide[0],count);int needed=WideCharToMultiByte(CP_UTF8,0,wide.data(),count,nullptr,0,nullptr,nullptr);std::string replacement(needed,'\0');if(needed)WideCharToMultiByte(CP_UTF8,0,wide.data(),count,&replacement[0],needed,nullptr,nullptr);size_t at=0;while((at=target.find("[N]",at))!=std::string::npos){target.replace(at,3,replacement);at+=replacement.size();}}
    found=true;return avzh::utf8(target);
}
int short_low(uint32_t value){return static_cast<short>(value&0xffff);}
int short_high(uint32_t value){return static_cast<short>(value>>16);}
}

extern "C" int __cdecl TryRender(unsigned align,const uint32_t* args) noexcept {
    if(!enabled || !wglGetCurrentContext())return 0;
    try{
        bool found=false;auto text=localized(reinterpret_cast<const char*>(args[0]),found);if(!found)return 0;
        avzh::TextState state;state.settings=font_settings;state.align=static_cast<short>(align);state.font=short_low(args[1]);state.red=short_low(args[2])/31.0f;state.green=short_low(args[3])/31.0f;state.blue=short_low(args[4])/31.0f;state.alpha=at<float>(0x5d0788);
        state.top=short_low(args[5]);state.left=short_high(args[5]);state.bottom=short_low(args[6]);state.right=short_high(args[6]);
        state.screen_width=at<int>(0x6bf33c);state.screen_height=at<int>(0x6bf340);if(state.screen_width<=0 || state.screen_height<=0 || state.right<=state.left)return 0;
        state.clip=at<unsigned char>(0x6bed4b)==0;state.clip_top=at<short>(0x6043ec);state.clip_left=at<short>(0x6043ee);state.clip_bottom=at<short>(0x6043f0);state.clip_right=at<short>(0x6043f2);
        auto result=renderer.draw(text,state);at<short>(0x6bef1c)=static_cast<short>(std::min(32767,result.height));at<short>(0x6bf32c)=static_cast<short>(result.last_x);at<short>(0x6bf330)=static_cast<short>(result.last_y);
        uintptr_t font=0x5c30b0;switch(state.font){case 14:font=0x5c36d0;break;case 15:font=0x5c33c0;break;case 16:case 18:font=0x5c39e0;break;case 20:case 22:case 24:font=0x5c3cf0;break;}
        at<uintptr_t>(0x6bf328)=game_base+font-0x400000;at<float>(0x5d078c)=1;at<float>(0x5d0790)=1;at<float>(0x5d0794)=1;return 1;
    }catch(const std::exception& error){log(std::string("render fallback: ")+error.what());return 0;}catch(...){log("render fallback: unexpected exception");return 0;}
}
extern "C" int __cdecl TryMeasure(const char* source) noexcept {
    if(!enabled)return -1;
    try{bool found=false;auto text=localized(source,found);if(!found)return -1;at<uintptr_t>(0x6bf328)=game_base+0x1c30b0;return std::min(32767,renderer.measure(text,font_settings.step(12)));}catch(...){return -1;}
}
static avzh::CameraActor read_party_actor(int index,int layer) noexcept {
    const uintptr_t actor=0x742368+index*0x19ac;
    avzh::CameraActor a;
    a.x=at<int>(actor+0x20);a.y=at<int>(actor+0x24);a.motion=at<short>(actor+0x157a);
    a.valid=at<short>(actor+0x30)==layer && at<short>(actor+2)>=0 &&
        at<short>(actor+0x46c)>=0 && at<short>(actor+0x1e)==2 &&
        a.x>=0 && a.y>=0 && a.x<=32768 && a.y<=32768;
    return a;
}

extern "C" unsigned __cdecl ScaleWalkSpeed(unsigned input,uintptr_t position,uintptr_t caller) noexcept {
    if(movement_percent<=100 || caller!=game_base+0x4160a ||
        at<short>(0x6bed48)!=10 || at<short>(0x6bed4c)!=0 || at<unsigned char>(0x6bed47)!=0)return input;
    const int layer=at<short>(0x73b90c);
    const int actor=read_party_actor(0,layer).valid?0:1;
    if(position!=game_base+0x342388+actor*0x19ac || !read_party_actor(actor,layer).valid)return input;
    const int speed=static_cast<short>(input);
    if(speed<=0)return input;
    const unsigned scaled=std::min(32767u,(speed*movement_percent+50u)/100u);
    return (input&0xffff0000u)|scaled;
}

// The native vector routine reads AX/ESI and returns with RET 8. Keep its
// computed deltas and restore the nominal speed it saves for the next step.
extern "C" __declspec(naked) void WalkVectorEntry(){
    __asm {
        push ebp
        mov ebp,esp
        push eax
        pushfd
        pushad
        push dword ptr[ebp+4]
        push esi
        push eax
        call ScaleWalkSpeed
        add esp,12
        mov dword ptr[esp+28],eax
        popad
        popfd
        push eax
        push dword ptr[ebp+12]
        push dword ptr[ebp+8]
        call dword ptr[g_original_walk_vector]
        pushfd
        push eax
        mov eax,dword ptr[ebp-4]
        cmp ax,word ptr[ebp-8]
        je keep_nominal_speed
        mov word ptr[esi+0x12],ax
    keep_nominal_speed:
        pop eax
        popfd
        mov esp,ebp
        pop ebp
        ret 8
    }
}
namespace {
uint32_t screen_point(int x,int y) noexcept {
    return (static_cast<uint32_t>(static_cast<uint16_t>(x))<<16)|static_cast<uint16_t>(y);
}
}

extern "C" void __cdecl DrawInteractionMarkers() noexcept {
    const short mode=at<short>(0x6bed48);
    if(!interaction_markers_enabled || (mode!=10 && mode!=15) || at<short>(0x6bed4c)!=0 ||
        at<unsigned char>(0x6bee3b)==0 || at<unsigned char>(0x6bee3a)!=0 ||
        GetForegroundWindow()!=at<HWND>(0x6bed20))return;
    const short layer=at<short>(0x73b90c);
    if(layer<0 || layer>=2)return;

    const int left=std::max(at<short>(0x6043ee),at<short>(0x6043fe));
    const int top=std::max(at<short>(0x6043ec),at<short>(0x6043fc));
    const int right=std::min(at<short>(0x6043f2),at<short>(0x604402));
    const int bottom=std::min(at<short>(0x6043f0),at<short>(0x604400));
    constexpr int marker_width=22,marker_height=28;
    if(right-left<marker_width || bottom-top<marker_height)return;
    const uint32_t clip_start=screen_point(left,top),clip_end=screen_point(right,bottom);
    using DrawRect=void(__cdecl*)(float,float,float,float,uint32_t,uint32_t,uint32_t,uint32_t);
    using Visible=unsigned char(__cdecl*)(int,int,int,int,int);
    auto draw=reinterpret_cast<DrawRect>(game_base+0x76c0);
    auto visible=reinterpret_cast<Visible>(game_base+0xa900);
    auto rect=[&](int x,int y,int width,int height,float red,float green,float blue){
        draw(red,green,blue,1.0f,screen_point(x,y),screen_point(x+width,y+height),clip_start,clip_end);
    };
    std::array<bool,600> marked{};
    for(int slot=0;slot<1200;++slot){
        // Category 9 in the original world draw list is a scenery object.
        const int entry=at<int>(0x6af7f8+4*slot);
        if(entry<9000 || entry>=9600)continue;
        const int id=entry-9000;
        if(marked[id])continue;
        const uintptr_t object=0x8b33f0+id*0x490;
        if(at<short>(object+4)!=0 || at<short>(object+0x1c)!=layer)continue;
        const int definition=at<short>(object+2);
        constexpr int definition_limit=(0x73b5ec-0x714958)/0x58;
        if(definition<0 || definition>=definition_limit)continue;
        const int type=at<short>(0x714958+definition*0x58);
        // Native cursor hit-testing accepts active scenery types 10 through 19.
        if(type<10 || type>=20)continue;
        const int tile_x=at<short>(object+0x14),tile_y=at<short>(object+0x18);
        if(tile_x<0 || tile_x>=128 || tile_y<0 || tile_y>=128 ||
            at<signed char>(0x661cc8+tile_x*128+tile_y)<=0)continue;
        const int x0=at<short>(object+0x3a),y0=at<short>(object+0x38);
        const int x1=at<short>(object+0x3e),y1=at<short>(object+0x3c);
        if(x0>=x1 || y0>=y1 || x1<=left || x0>=right || y1<=top || y0>=bottom)continue;
        if(!visible(1,at<int>(object+0x28),at<int>(object+0x2c),
            at<int>(object+0x30),at<int>(object+0x34)))continue;
        marked[id]=true;

        const int x=std::clamp((x0+x1)/2-marker_width/2,left,right-marker_width);
        const int y=std::clamp(y0+2,top,bottom-marker_height);
        rect(x,y,marker_width,marker_height,1,1,1);
        rect(x+2,y+2,18,24,31,27,5);
        rect(x+9,y+5,4,11,1,1,1);
        rect(x+9,y+19,4,4,1,1,1);
    }
}

extern "C" __declspec(naked) void WorldLabelsEntry(){
    __asm {
        pushfd
        pushad
        call DrawInteractionMarkers
        popad
        popfd
        jmp dword ptr[g_original_world_labels]
    }
}

extern "C" void __cdecl UpdateCamera() noexcept {
    if(!camera_enabled)return;
    avzh::CameraFrame frame;frame.mode=at<short>(0x6bed48);frame.layer=at<short>(0x73b90c);
    // Native input/scroll suppression, ordinary gameplay only; never menus,
    // targeting modes, paused/scripted UI, background window, or enemy turns.
    frame.allowed=(frame.mode==10 || frame.mode==15) && at<short>(0x6bed4c)==0 &&
        at<unsigned char>(0x6bed47)==0 && frame.layer>=0 && frame.layer<2 &&
        GetForegroundWindow()==at<HWND>(0x6bed20);
    frame.tick=at<uint32_t>(0x6beeb8);frame.preferred=at<short>(0x5cf394);
    if(frame.allowed){
        for(int i=0;i<2;++i){
            frame.actors[i]=read_party_actor(i,frame.layer);
        }
    }
    auto target=camera_follow.update(frame);if(!target.follow)return;
    auto position=avzh::camera_position(target.x,target.y);
    at<int>(0xeb84b8)=position.x;at<int>(0xeb84bc)=position.y;
    at<int>(0xeb84c0)=position.screen_x;at<int>(0xeb84c4)=position.screen_y;
}

extern "C" __declspec(naked) void CameraEntry(){
    __asm {
        pushfd
        pushad
        call UpdateCamera
        popad
        popfd
        jmp dword ptr[g_original_camera]
    }
}
extern "C" int __cdecl InventoryKey(int key) noexcept {
    if(!inventory_toggle_enabled || at<short>(0x6bed4c)!=10 ||
        (at<short>(0x6bed48)!=10 && at<short>(0x6bed48)!=15) ||
        at<unsigned char>(0x6bee47)!=0 || at<unsigned char>(0x6b1cdd)!=0 || at<unsigned char>(0x6b1cdf)!=0)return key;
    // Runtime binding tables, exactly as the original inventory-open branch:
    // key in DX, input event and modifier mode as caller-cleaned stack args.
    unsigned binding=static_cast<unsigned short>(at<short>(0x60444e));
    unsigned modifiers=static_cast<unsigned short>(at<short>(0x6044ee));
    if(binding==0)return key;
    void* match=reinterpret_cast<void*>(game_base+0x2d2f0);unsigned char matched=0;
    __asm {
        push modifiers
        push key
        mov edx,binding
        mov eax,match
        call eax
        add esp,8
        mov matched,al
    }
    // Delegate all closing/cancel/held-item rules to the existing Escape route.
    return matched?0x18:key;
}
extern "C" __declspec(naked) void KeyboardEntry(){
    __asm {
        pushfd
        pushad
        push dword ptr[esp+40]
        call InventoryKey
        add esp,4
        mov dword ptr[esp+40],eax
        popad
        popfd
        jmp dword ptr[g_original_keyboard]
    }
}

// The shipped x86 ABI uses ECX for alignment, EDX for width-query text,
// caller-cleaned stack arguments, and a plain RET. Both prologues are nine
// relocation-free bytes verified against REA evidence and the full EXE hash.
extern "C" __declspec(naked) void TextEntry(){
    __asm {
        push ebp
        mov ebp,esp
        pushfd
        pushad
        lea eax,[ebp+8]
        push eax
        push ecx
        call TryRender
        add esp,8
        test eax,eax
        jnz handled
        popad
        popfd
        pop ebp
        jmp dword ptr[g_original_text]
    handled:
        popad
        popfd
        pop ebp
        ret
    }
}
extern "C" __declspec(naked) void MeasureEntry(){
    __asm {
        pushfd
        pushad
        push edx
        call TryMeasure
        add esp,4
        cmp eax,-1
        je original
        mov dword ptr[esp+28],eax
        popad
        popfd
        ret
    original:
        popad
        popfd
        jmp dword ptr[g_original_measure]
    }
}
namespace {
static_assert(sizeof(void*)==4,"Avadon adapter requires x86");
BOOL CALLBACK initialize_adapter(PINIT_ONCE,void*,void**) noexcept {
    try{
        wchar_t executable[MAX_PATH]{};if(!GetModuleFileNameW(nullptr,executable,MAX_PATH))return TRUE;std::wstring path(executable);size_t separator=path.find_last_of(L"\\/");if(separator==std::wstring::npos)return TRUE;data_path=path.substr(0,separator)+L"\\AvadonChinese";
        log("initialize: adapter startup reached");
        if(file_exists(data_path+L"\\disabled.flag")){log("disabled.flag: forwarding only");return TRUE;}
        if(executable_hash(path)!="d3d897e0b0608aad52f22e09d9b2174653b5903e6de9b1cc8e396ebc3c72d44e"){log("unsupported executable: forwarding only");return TRUE;}
        dictionary.load(data_path+L"\\translations.bin");font_settings=avzh::FontSettings::load(data_path+L"\\font.ini");
        log("font: scale="+std::to_string(font_settings.percent)+"%; fit_labels="+std::to_string(font_settings.fit_labels));
        game_base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        void* text_entry=reinterpret_cast<void*>(game_base+0x6e080);void* measure_entry=reinterpret_cast<void*>(game_base+0x6df00);
        const unsigned char text_bytes[]={0x55,0x8b,0xec,0x81,0xec,0x40,0x08,0,0},measure_bytes[]={0x55,0x8b,0xec,0x81,0xec,0x14,0x04,0,0};
        if(memcmp(text_entry,text_bytes,9) || memcmp(measure_entry,measure_bytes,9)){log("entry signature mismatch: forwarding only");return TRUE;}
        MH_STATUS status=MH_Initialize();if(status!=MH_OK){log(std::string("hook initialization failed: ")+MH_StatusToString(status));return TRUE;}
        status=MH_CreateHook(text_entry,reinterpret_cast<void*>(&TextEntry),&g_original_text);
        if(status==MH_OK)status=MH_CreateHook(measure_entry,reinterpret_cast<void*>(&MeasureEntry),&g_original_measure);
        if(status!=MH_OK){MH_RemoveHook(MH_ALL_HOOKS);log(std::string("hook preparation failed: ")+MH_StatusToString(status));return TRUE;}
        const unsigned char camera_bytes[]={0x55,0x8b,0xec,0x83,0xec,0x5c};
        void* camera_entry=reinterpret_cast<void*>(game_base+0x32970);
        if(GetPrivateProfileIntW(L"Camera",L"FollowCharacter",0,(data_path+L"\\camera.ini").c_str())!=0){
            if(memcmp(camera_entry,camera_bytes,sizeof(camera_bytes))==0 &&
                MH_CreateHook(camera_entry,reinterpret_cast<void*>(&CameraEntry),&g_original_camera)==MH_OK){camera_enabled=true;log("camera: character 1 or character 2 when absent; native idle edge scrolling");}
            else log("camera: signature or hook mismatch; camera enhancement disabled");
        }
        const auto settings_path=data_path+L"\\camera.ini";
        if(file_exists(settings_path) && GetPrivateProfileIntW(L"Interaction",L"HighlightOnShift",1,settings_path.c_str())!=0){
            const unsigned char label_bytes[]={0x55,0x8b,0xec,0x83,0xec,0x1c};
            const unsigned char rect_bytes[]={0x55,0x8b,0xec,0x51,0x8b,0x55,0x18};
            const unsigned char sight_bytes[]={0x55,0x8b,0xec,0x83,0xec,0x08};
            void* labels=reinterpret_cast<void*>(game_base+0x350c0);
            if(memcmp(labels,label_bytes,sizeof(label_bytes))==0 &&
                memcmp(reinterpret_cast<void*>(game_base+0x76c0),rect_bytes,sizeof(rect_bytes))==0 &&
                memcmp(reinterpret_cast<void*>(game_base+0xa900),sight_bytes,sizeof(sight_bytes))==0 &&
                MH_CreateHook(labels,reinterpret_cast<void*>(&WorldLabelsEntry),&g_original_world_labels)==MH_OK){
                interaction_markers_enabled=true;
                log("interaction markers: hold Shift");
            }else log("interaction markers: signature or hook mismatch");
        }
        const auto configured_speed=GetPrivateProfileIntW(L"Movement",L"SpeedPercent",100,(data_path+L"\\camera.ini").c_str());
        movement_percent=static_cast<unsigned>(std::clamp(static_cast<int>(configured_speed),100,200));
        if(movement_percent>100){
            const unsigned char vector_bytes[]={0x55,0x8b,0xec,0x83,0xec,0x08};
            const unsigned char call_bytes[]={0x66,0x8b,0x43,0x32,0x8b,0xf7,0xe8,0x86,0xfd,0x00,0x00};
            void* vector_entry=reinterpret_cast<void*>(game_base+0x51390);
            if(memcmp(vector_entry,vector_bytes,sizeof(vector_bytes))==0 &&
                memcmp(reinterpret_cast<void*>(game_base+0x415ff),call_bytes,sizeof(call_bytes))==0 &&
                MH_CreateHook(vector_entry,reinterpret_cast<void*>(&WalkVectorEntry),&g_original_walk_vector)==MH_OK){
                log("movement speed: "+std::to_string(movement_percent)+"%");
            }else log("movement speed: signature or hook mismatch");
        }
        const unsigned char keyboard_bytes[]={0x55,0x8b,0xec,0x83,0xe4,0xf8,0x83,0xec,0x0c};
        const unsigned char matcher_bytes[]={0x55,0x8b,0xec,0x83,0xec,0x78};
        void* keyboard_entry=reinterpret_cast<void*>(game_base+0x67370);
        if(file_exists(data_path+L"\\camera.ini") && GetPrivateProfileIntW(L"Inventory",L"ToggleHotkey",1,(data_path+L"\\camera.ini").c_str())!=0){
            if(memcmp(keyboard_entry,keyboard_bytes,sizeof(keyboard_bytes))==0 &&
                memcmp(reinterpret_cast<void*>(game_base+0x2d2f0),matcher_bytes,sizeof(matcher_bytes))==0 &&
                MH_CreateHook(keyboard_entry,reinterpret_cast<void*>(&KeyboardEntry),&g_original_keyboard)==MH_OK){inventory_toggle_enabled=true;log("inventory: current custom hotkey also invokes native Escape while inventory is open");}
            else log("inventory: signature or hook mismatch; inventory toggle disabled");
        }
        enabled=true;status=MH_EnableHook(MH_ALL_HOOKS);
        if(status!=MH_OK){enabled=false;MH_DisableHook(MH_ALL_HOOKS);log(std::string("hook activation failed: ")+MH_StatusToString(status));return TRUE;}
        log("enabled: offline pre-format localization; "+std::to_string(dictionary.size())+" keys; "+std::to_string(dictionary.patterns())+" format patterns");
    }catch(const std::exception& error){log(std::string("disabled: ")+error.what());}catch(...){log("disabled: initialization exception");}return TRUE;
}
BOOL CALLBACK initialize_real(PINIT_ONCE,void*,void**) noexcept {
    wchar_t system[MAX_PATH]{};if(!GetSystemDirectoryW(system,MAX_PATH))return FALSE;std::wstring path=std::wstring(system)+L"\\winmm.dll";real_winmm=LoadLibraryW(path.c_str());if(!real_winmm)return FALSE;
    for(unsigned i=0;i<AVZH_FORWARD_COUNT;++i)g_forwards[i]=GetProcAddress(real_winmm,avzh_forward_names[i]?avzh_forward_names[i]:MAKEINTRESOURCEA(avzh_forward_ordinals[i]));return TRUE;
}
}
extern "C" void __cdecl ResolveForward(unsigned index) noexcept {
    if(!InitOnceExecuteOnce(&real_once,initialize_real,nullptr,nullptr) || index>=AVZH_FORWARD_COUNT || !g_forwards[index])ExitProcess(ERROR_PROC_NOT_FOUND);
}
extern "C" DWORD WINAPI ProxyClock(){ResolveForward(AVZH_CLOCK_INDEX);InitOnceExecuteOnce(&adapter_once,initialize_adapter,nullptr,nullptr);return reinterpret_cast<DWORD(WINAPI*)()>(g_forwards[AVZH_CLOCK_INDEX])();}
namespace {
DWORD WINAPI Bootstrap(void*) noexcept {
    // Windows serializes DLL thread notifications: this entry runs after the
    // attaching DllMain returns. Hashing, I/O and MinHook stay outside loader lock.
    // The timer import is only a fallback when QueryPerformanceCounter is absent.
    InitOnceExecuteOnce(&adapter_once,initialize_adapter,nullptr,nullptr);
    return 0;
}
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,void*){
    if(reason==DLL_PROCESS_ATTACH){
        module_handle=module;
        HANDLE worker=CreateThread(nullptr,0,Bootstrap,nullptr,0,nullptr);
        if(worker)CloseHandle(worker); // Never join/wait inside DllMain.
    }
    return TRUE;
}

#ifdef AVZH_SELF_TEST
// Present only in the separately compiled component-test EXE, never in winmm.dll.
extern "C" void FixtureInitialize(void* memory,const wchar_t* dictionary_path,const wchar_t* logs){
    game_base=reinterpret_cast<uintptr_t>(memory);data_path=logs;dictionary.load(dictionary_path);
    at<int>(0x6bf33c)=320;at<int>(0x6bf340)=160;at<float>(0x5d0788)=1;
    at<short>(0x6043ec)=0;at<short>(0x6043ee)=0;at<short>(0x6043f0)=160;at<short>(0x6043f2)=320;
    if(MH_Initialize()!=MH_OK || MH_CreateHook(reinterpret_cast<void*>(game_base+0x6e080),reinterpret_cast<void*>(&TextEntry),&g_original_text)!=MH_OK || MH_CreateHook(reinterpret_cast<void*>(game_base+0x6df00),reinterpret_cast<void*>(&MeasureEntry),&g_original_measure)!=MH_OK)throw std::runtime_error("Fixture hook creation failed");
    enabled=true;if(MH_EnableHook(MH_ALL_HOOKS)!=MH_OK)throw std::runtime_error("Fixture hook activation failed");
}
extern "C" void FixtureFinish(){enabled=false;camera_enabled=false;inventory_toggle_enabled=false;camera_follow.reset();MH_DisableHook(MH_ALL_HOOKS);MH_Uninitialize();}
extern "C" bool FixtureNameExpansion(){bool found=false;auto text=localized("You are [N]?",found);return found && text.find(L"TestHero")!=std::wstring::npos && text.find(L"[N]")==std::wstring::npos;}
extern "C" void FixtureFontScale(int percent){font_settings.percent=percent;}
extern "C" void FixtureInteractionEnable(){
    void* entry=reinterpret_cast<void*>(game_base+0x350c0);
    if(MH_CreateHook(entry,reinterpret_cast<void*>(&WorldLabelsEntry),&g_original_world_labels)!=MH_OK ||
        MH_EnableHook(entry)!=MH_OK)throw std::runtime_error("Fixture interaction hook failed");
    interaction_markers_enabled=true;
}
extern "C" void FixtureMovementSpeed(unsigned percent){movement_percent=percent;}
extern "C" void FixtureMovementEnable(){
    void* entry=reinterpret_cast<void*>(game_base+0x51390);
    if(MH_CreateHook(entry,reinterpret_cast<void*>(&WalkVectorEntry),&g_original_walk_vector)!=MH_OK ||
        MH_EnableHook(entry)!=MH_OK)throw std::runtime_error("Fixture movement hook failed");
}
extern "C" void FixtureCameraEnable(){
    camera_enabled=true;camera_follow.reset();
    if(MH_CreateHook(reinterpret_cast<void*>(game_base+0x32970),reinterpret_cast<void*>(&CameraEntry),&g_original_camera)!=MH_OK || MH_EnableHook(g_original_camera?reinterpret_cast<void*>(game_base+0x32970):nullptr)!=MH_OK)throw std::runtime_error("Fixture camera hook failed");
}
extern "C" { int g_fixture_key_modifiers=0; }
extern "C" __declspec(naked) void FixtureKeyMatcher(){
    __asm {
        cmp edx,dword ptr[esp+4]
        jne fixture_no_match
        mov eax,dword ptr[esp+8]
        cmp eax,dword ptr[g_fixture_key_modifiers]
        jne fixture_no_match
        mov eax,1
        ret
    fixture_no_match:
        xor eax,eax
        ret
    }
}
extern "C" void FixtureKeyModifiers(int mode){g_fixture_key_modifiers=mode;}
extern "C" void FixtureInventoryEnable(){
    unsigned char matcher[]={0xb8,0,0,0,0,0xff,0xe0};
    auto target=reinterpret_cast<uintptr_t>(&FixtureKeyMatcher);memcpy(matcher+1,&target,4);
    memcpy(reinterpret_cast<void*>(game_base+0x2d2f0),matcher,sizeof(matcher));
    if(MH_CreateHook(reinterpret_cast<void*>(game_base+0x67370),reinterpret_cast<void*>(&KeyboardEntry),&g_original_keyboard)!=MH_OK || MH_EnableHook(reinterpret_cast<void*>(game_base+0x67370))!=MH_OK)throw std::runtime_error("Fixture keyboard hook failed");
    inventory_toggle_enabled=true;
}
#endif

#include "forward_stubs.inc"
