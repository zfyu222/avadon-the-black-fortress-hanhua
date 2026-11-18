#pragma once
#include <array>
#include <algorithm>
#include <cstdint>
#include <cstdlib>

namespace avzh {
struct CameraActor { bool valid=false;int x=0,y=0,motion=0; };
struct CameraFrame {
    bool allowed=false;int mode=0,layer=0,preferred=-1;uint32_t tick=0;
    std::array<CameraActor,8> actors{};
};
struct CameraTarget { bool follow=false;int actor=-1,x=0,y=0; };
// No OS calls or game writes: the adapter samples native state on the game thread.
class CameraFollow {
    CameraFrame previous_{};bool sampled_=false;
    int tracking_=-1;uint32_t last_motion_=0;
public:
    void reset(){sampled_=false;tracking_=-1;}
    CameraTarget update(const CameraFrame& frame){
        CameraTarget result;
        const int actor=frame.actors[0].valid?0:frame.actors[1].valid?1:-1;
        if(!frame.allowed || actor<0 || (frame.mode==15 && frame.preferred!=actor)){reset();return result;}
        if(!sampled_ || frame.layer!=previous_.layer || frame.mode!=previous_.mode){
            previous_=frame;sampled_=true;tracking_=-1;return result;
        }
        auto moving=[&](int id){
            if(id<0 || id>=8)return false;
            const auto& a=frame.actors[id];const auto& b=previous_.actors[id];
            // A fresh actor, teleport, or placement is not a walking step.
            return a.valid && b.valid && a.motion>0 && a.motion<11 &&
                (a.x!=b.x || a.y!=b.y) && std::abs(a.x-b.x)<=256 && std::abs(a.y-b.y)<=256;
        };
        // Character 2 takes over only when character 1 is absent.
        if(tracking_!=actor)tracking_=-1;
        const int choice=moving(actor)?actor:-1;
        if(choice>=0){tracking_=choice;last_motion_=frame.tick;}
        else if(tracking_>=0){
            const auto& a=frame.actors[tracking_];
            const auto& b=previous_.actors[tracking_];
            if(!a.valid || !b.valid || std::abs(a.x-b.x)>256 || std::abs(a.y-b.y)>256 ||
               a.motion<=0 || a.motion>=11 || frame.tick-last_motion_>96 ||
               (frame.mode==15 && tracking_!=frame.preferred))tracking_=-1;
        }
        if(tracking_>=0){
            result.follow=true;result.actor=tracking_;
            result.x=frame.actors[tracking_].x;result.y=frame.actors[tracking_].y;
        }
        previous_=frame;return result;
    }
};
struct CameraPosition { int x=0,y=0,screen_x=0,screen_y=0; };
inline CameraPosition camera_position(int x,int y){
    // Same world->isometric conversion as native scene load and map click.
    CameraPosition result;result.x=std::max(-512,std::min(33280,x));result.y=std::max(-512,std::min(33280,y));
    result.screen_x=(result.x-result.y)*15/64;
    result.screen_y=(result.x+result.y)*10/64;
    return result;
}
}
