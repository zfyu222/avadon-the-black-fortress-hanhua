#pragma once
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <functional>
#include <regex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace avzh {
struct FormatPart { std::string literal, spec; };
inline std::vector<FormatPart> format_parts(const std::string& text) {
    // No space flag: ordinary prose such as "5% chance" is not a printf call.
    static const std::regex token(R"(%(?:[0-9]+\$)?[-+0#]*[0-9]*(?:\.[0-9]+)?(?:hh|ll|[hlLzjt])?[diuoxXfFeEgGaAcsp%])");
    std::vector<FormatPart> parts; size_t begin=0;
    for (std::sregex_iterator it(text.begin(),text.end(),token),end;it!=end;++it) {
        size_t at=static_cast<size_t>(it->position());
        parts.push_back({text.substr(begin,at-begin),it->str()});begin=at+it->length();
    }
    parts.push_back({text.substr(begin),{}});return parts;
}
inline std::string regex_literal(const std::string& text) {
    std::string out;for(char c:text){if(std::string(R"(\.^$|()[]{}*+?)").find(c)!=std::string::npos)out+='\\';out+=c;}return out;
}
struct Pattern { std::regex expression; std::vector<FormatPart> target; size_t specificity; bool require_known_argument; };
class Dictionary {
    std::unordered_map<std::string,std::string> exact_;
    std::vector<Pattern> patterns_;
public:
    void add(const std::string& source,const std::string& target) {
        auto found=exact_.find(source);
        if(found!=exact_.end() && found->second!=target)throw std::runtime_error("Ambiguous dictionary source");
        exact_[source]=target;
    }
    void prepare() {
        patterns_.clear();
        for(const auto& pair:exact_) {
            auto source=format_parts(pair.first),target=format_parts(pair.second);size_t captures=0,literals=0,words=0;bool has_string=false,has_number=false;std::string expression="^";
            for(const auto& part:source){bool in_word=false;for(unsigned char c:part.literal){bool letter=(c>='A'&&c<='Z')||(c>='a'&&c<='z');if(letter&&!in_word)++words;in_word=letter;}expression+=regex_literal(part.literal);literals+=part.literal.size();if(part.spec=="%%"){expression+='%';++literals;}else if(!part.spec.empty()){
                // Positional conversion is left to an explicitly supported adapter.
                if(part.spec.find('$')!=std::string::npos){captures=0;break;}
                char kind=part.spec.back();
                if(kind=='s'){expression+="(.*?)";has_string=true;}
                else if(kind=='c')expression+="(.)";
                else if(std::string("diu").find(kind)!=std::string::npos)expression+="([ +\\-]*[0-9]+)";
                else if(std::string("oxXp").find(kind)!=std::string::npos)expression+="((?:0x)?[0-9a-fA-F]+)";
                else expression+="([ +\\-]*(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+\\-]?[0-9]+)?)";
                if(kind!='s' && kind!='c')has_number=true;++captures;
            }}
            if(!captures || literals<2)continue;
            size_t target_captures=0;for(const auto& p:target)if(!p.spec.empty() && p.spec!="%%")++target_captures;
            if(captures!=target_captures)throw std::runtime_error("Printf argument count differs");
            patterns_.push_back({std::regex(expression+"$",std::regex::ECMAScript|std::regex::optimize),std::move(target),literals,has_string && words<2 && !(has_number && words>0)});
        }
        std::stable_sort(patterns_.begin(),patterns_.end(),[](const Pattern&a,const Pattern&b){return a.specificity>b.specificity;});
    }
    bool lookup(const std::string& source,std::string& target,unsigned depth=0) const {
        auto found=exact_.find(source);if(found!=exact_.end()){target=found->second;return true;}
        if(depth>2 || source.size()>4096)return false;
        for(const auto& pattern:patterns_){std::smatch match;if(!std::regex_match(source,match,pattern.expression))continue;
            std::string candidate;size_t index=1;bool known_argument=false;
            for(const auto& part:pattern.target){candidate+=part.literal;if(part.spec=="%%")candidate+='%';else if(!part.spec.empty()){
                std::string argument=match[index++].str(),localized;
                if(part.spec.back()=='s' && lookup(argument,localized,depth+1) && localized!=argument){candidate+=localized;known_argument=true;}else candidate+=argument;
            }}if(pattern.require_known_argument && !known_argument)continue;target=std::move(candidate);return true;
        }return false;
    }
    size_t size()const{return exact_.size();}
    size_t patterns()const{return patterns_.size();}
    void load(const std::wstring& path) {
        std::ifstream input(path.c_str(),std::ios::binary);if(!input)throw std::runtime_error("Missing translation dictionary");
        auto number=[&](){uint32_t value=0;input.read(reinterpret_cast<char*>(&value),4);if(!input)throw std::runtime_error("Truncated dictionary");return value;};
        char magic[8];input.read(magic,8);if(std::string(magic,8)!=std::string("AVZH1\0\0\0",8))throw std::runtime_error("Dictionary magic mismatch");
        uint32_t count=number();if(count>100000)throw std::runtime_error("Dictionary count limit");
        for(uint32_t i=0;i<count;++i){uint32_t a=number(),b=number();if(a>65536 || b>65536)throw std::runtime_error("Dictionary string limit");std::string source(a,'\0'),target(b,'\0');input.read(&source[0],a);input.read(&target[0],b);if(!input)throw std::runtime_error("Truncated dictionary record");add(source,target);}
        if(input.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Trailing dictionary bytes");prepare();
    }
};
inline bool closing(wchar_t c){return std::wstring(L"，。！？；：、）》」』】〕…％%”’").find(c)!=std::wstring::npos;}
inline std::vector<std::wstring> wrap(const std::wstring& text,int limit,const std::function<int(const std::wstring&)>& measure){
    std::vector<std::wstring> lines;std::wstring line;
    auto flush=[&](){while(!line.empty() && line.back()==L' ')line.pop_back();lines.push_back(line);line.clear();};
    for(size_t i=0;i<text.size();++i){wchar_t c=text[i];if(c==L'\r'){if(i+1<text.size() && text[i+1]==L'\n')++i;flush();continue;}if(c==L'\n'||c==L'|'){flush();continue;}
        std::wstring unit(1,c);if(c>=0xd800 && c<=0xdbff && i+1<text.size() && text[i+1]>=0xdc00 && text[i+1]<=0xdfff)unit+=text[++i];
        if(!line.empty() && measure(line+unit)>limit){
            size_t space=line.find_last_of(L' ');
            if(space!=std::wstring::npos && space>0){std::wstring tail=line.substr(space+1);line.resize(space);flush();line=tail;}
            else if(closing(c) && line.size()>1){size_t at=line.size()-1;if(line[at]>=0xdc00 && line[at]<=0xdfff && at && line[at-1]>=0xd800 && line[at-1]<=0xdbff)--at;std::wstring tail=line.substr(at);line.resize(at);flush();line=tail;}
            else flush();
        }
        if(line.empty() && c==L' ')continue;line+=unit;
    }
    if(!line.empty() || lines.empty())flush();return lines;
}
} // namespace avzh
