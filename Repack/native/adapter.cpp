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
#include "forward_metadata.hpp"
#include "MinHook.h"

#pragma comment(lib,"bcrypt.lib")
#pragma comment(lib,"gdi32.lib")
#pragma comment(lib,"user32.lib")
#pragma comment(lib,"opengl32.lib")

extern "C" { FARPROC g_forwards[AVZH_FORWARD_COUNT]{};void* g_original_text=nullptr;void* g_original_measure=nullptr; }
namespace {
HMODULE module_handle=nullptr,real_winmm=nullptr;
INIT_ONCE real_once=INIT_ONCE_STATIC_INIT,adapter_once=INIT_ONCE_STATIC_INIT;
uintptr_t game_base=0;bool enabled=false;
std::wstring data_path;
avzh::Dictionary dictionary;
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
        avzh::TextState state;state.align=static_cast<short>(align);state.font=short_low(args[1]);state.red=short_low(args[2])/31.0f;state.green=short_low(args[3])/31.0f;state.blue=short_low(args[4])/31.0f;state.alpha=at<float>(0x5d0788);
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
    try{bool found=false;auto text=localized(source,found);if(!found)return -1;at<uintptr_t>(0x6bf328)=game_base+0x1c30b0;return std::min(32767,renderer.measure(text,13));}catch(...){return -1;}
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
        dictionary.load(data_path+L"\\translations.bin");game_base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        void* text_entry=reinterpret_cast<void*>(game_base+0x6e080);void* measure_entry=reinterpret_cast<void*>(game_base+0x6df00);
        const unsigned char text_bytes[]={0x55,0x8b,0xec,0x81,0xec,0x40,0x08,0,0},measure_bytes[]={0x55,0x8b,0xec,0x81,0xec,0x14,0x04,0,0};
        if(memcmp(text_entry,text_bytes,9) || memcmp(measure_entry,measure_bytes,9)){log("entry signature mismatch: forwarding only");return TRUE;}
        MH_STATUS status=MH_Initialize();if(status!=MH_OK){log(std::string("hook initialization failed: ")+MH_StatusToString(status));return TRUE;}
        status=MH_CreateHook(text_entry,reinterpret_cast<void*>(&TextEntry),&g_original_text);
        if(status==MH_OK)status=MH_CreateHook(measure_entry,reinterpret_cast<void*>(&MeasureEntry),&g_original_measure);
        if(status!=MH_OK){MH_RemoveHook(MH_ALL_HOOKS);log(std::string("hook preparation failed: ")+MH_StatusToString(status));return TRUE;}
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
extern "C" void FixtureFinish(){enabled=false;MH_DisableHook(MH_ALL_HOOKS);MH_Uninitialize();}
extern "C" bool FixtureNameExpansion(){bool found=false;auto text=localized("You are [N]?",found);return found && text.find(L"TestHero")!=std::wstring::npos && text.find(L"[N]")==std::wstring::npos;}
#endif

#include "forward_stubs.inc"
