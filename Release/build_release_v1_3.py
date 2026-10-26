"""Documentation-only update; retain exactly the tested v1.2 installer bytes."""
import build_release_v1_2 as base
P=base.P
VERSION='1.3'
ARCHIVE=P/f'Dispatch/阿瓦登：黑色要塞_子非鱼汉化{VERSION}.zip'
base.VERSION=VERSION
base.ARCHIVE=ARCHIVE
base.CHANGES='下载地址、订阅及反馈移至说明最前面；安装与卸载方式不变。'
if __name__=='__main__':base.build();base.verify()
