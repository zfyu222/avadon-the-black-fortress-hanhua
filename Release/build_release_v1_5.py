"""Publish the reviewed image build-v9 with the simple Windows installer."""
import build_release_v1_2 as base
P=base.P
VERSION='1.5'
ARCHIVE=P/f'Dispatch/阿瓦登：黑色要塞_子非鱼汉化{VERSION}.zip'
base.VERSION=VERSION
base.ARCHIVE=ARCHIVE
base.INSTALLATION_PATH=P/'Repack/RELEASE_CANDIDATE.json'
base.RELEASE_DATE='2026-10-29'
base.PAYLOAD_BASELINE=None
base.CHANGES='优化19张中文图片：去除遮挡原画的背景色块，修补底纹，调整字体、配色及字号，使地图与界面文字更协调。'
if __name__=='__main__':base.build();base.verify()
