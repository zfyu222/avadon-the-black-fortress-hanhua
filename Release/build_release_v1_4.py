"""Player guide update; game payload and installer stay unchanged."""
import build_release_v1_2 as base
P=base.P
VERSION='1.4'
ARCHIVE=P/f'Dispatch/阿瓦登：黑色要塞_子非鱼汉化{VERSION}.zip'
base.VERSION=VERSION
base.ARCHIVE=ARCHIVE
base.CHANGES='AI翻译说明补充“请适当降低预期”，移除运行情况栏目。'
if __name__=='__main__':base.build();base.verify()
