"""Import explicit visual readings authored after viewing the bound images.
Coordinates supplied below are original pixels, converted mechanically to 0..1000.
Never derive decisions or text from model scores or proposals.
"""
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'work'

def save(pack_id,readings,seen_ids):
    pack=json.loads((WORK/'tiered/agent'/pack_id/'package.json').read_text(encoding='utf-8'))
    jobs={int(x['id']):x for x in pack['jobs']};records=[]
    for n in seen_ids:
        job=jobs[n];w,h=job['size']
        if n in readings:
            regions,unreadable,reason=readings[n]
            records.append(dict(id=str(n),status='text' if regions else 'uncertain',reason=reason,unreadable=unreadable,
                regions=[{'text':t,'box':[round(v/(w if i%2==0 else h)*1000,3) for i,v in enumerate(box)]} for t,box in regions]))
        else:
            records.append(dict(id=str(n),status='no_text',reason='已实际查看此编号的绑定联系表：仅见角色/动物动作帧、物体、纹理、光效或插画，没有可辨认的文字。',unreadable=False,regions=[]))
    dest=ROOT/'visual_reviews'/f'{pack_id}.reply.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(dest)

def pack1():
    r={}
    r[4]=([('THE KVA',[320,48,610,112]),('WRETCH LANDS',[288,372,692,566])],True,'已查看原始地图：两处地名可读；左边界另有被截断的地名片段，不补全。')
    r[9]=([('A - Terrain Screen',[218,28,386,51]),('B - Buttons',[218,52,343,73]),('C - Party Roster',[218,75,370,96]),('D - Automap',[218,97,355,119]),('A',[90,64,107,84]),('B',[82,135,101,153]),('C',[9,20,26,41]),('D',[181,17,201,38])],False,'逐字核对教程图的四条说明及截图上的 A/B/C/D 标记。')
    r[24]=([('Spiderweb',[0,0,515,121]),('TM',[512,21,532,39]),('SOFTWARE',[105,109,540,145])],False,'原图是 Spiderweb SOFTWARE 标志，右上角还有小型 TM。')
    medals=[('10',[79,22,114,52]),('20',[142,22,179,52]),('30',[207,22,248,52]),('The Beraza\nWoods',[8,80,63,103]),('R.I.P.',[84,277,112,291]),('10',[151,294,192,319]),('50',[78,354,119,383]),('Castle\nVebeaux',[222,347,325,374]),('!',[9,210,22,246])]
    r[55]=(medals,True,'原图及最近邻放大核对了数字、地图小字和墓碑；血迹遮挡的地图字不补全，圆章内的星形是徽记。')
    r[61]=([('A - Items on Ground',[161,15,310,35]),('B - Equipped Items',[161,35,307,54]),('C - Quick Use Items',[161,54,310,73]),('D - Your Pack',[161,74,274,92]),('E - Scarabs',[161,93,263,111]),('A',[111,90,125,105]),('B',[39,40,50,54]),('C',[37,98,49,112]),('D',[109,34,122,48]),('E',[22,62,34,77])],True,'教程五条注释及 A-E 标记可读；嵌入的库存截图还有若干极小字，无法逐字可靠读全。')
    r[94]=([('AVADON',[0,0,303,66]),('the BLACK FORTRESS',[5,61,297,96])],False,'已查看标题原图，主标题大写 AVADON，副标题以小写 the 开头。')
    gray=[x for x in medals if x[0]!='Castle\nVebeaux']
    gray += [('Castle\nVebeaux',[222,347,325,374])]
    for i in range(5): gray.append(('?',[i*65+14,144,i*65+52,190]))
    r[95]=(gray,True,'核对灰度成就图的数字、问号及可读地图/墓碑字；血迹遮挡和细小残字保持未决。')
    save('8407ab472e3967070041c7aa773114242bf56300ceff289ce0944661598c0d3d',r,range(1,101))

def pack2():
    r={}
    r[11]=([('?', [199,55,223,86]),('?', [299,12,314,30])],False,'图集中两个清晰问号，其余为技能/状态图标，不按模型将纹理读成文字。')
    labels=['Return To Game','Save Game','Load Saved Game','Game Settings','Keyboard Shortcuts','Return To Title Screen','Quit']
    boxes=[[47,2,246,27],[72,57,227,84],[36,85,257,110],[57,141,234,166],[23,169,269,194],[10,225,282,249],[116,253,174,278]]
    r[41]=(list(zip(labels,boxes)),False,'已逐行查看暂停菜单，保留各行大小写。')
    r[56]=([('The Adventure Continues ...',[9,0,346,27]),('THE WYLDRYLM',[209,205,285,222])],True,'宣传拼图标题及地图的一处完整地名可读；截图的极小对话字和被覆盖的地图字不补写。')
    r[62]=([('Map',[735,2,774,24]),('Roster',[781,499,828,522]),('Loading',[134,594,207,616]),('Loading',[134,630,207,651]),('?', [762,590,778,614]),('?', [319,740,338,773])],False,'查看全尺寸 UI 图集，核对地图/队伍标题、两处加载文字及问号按钮。')
    r[74]=([('THE TAWON EMPIRE',[320,176,532,210]),('The Beraza\nWoods',[154,260,209,286]),('Castle\nVebeaux',[240,277,287,301]),('DHARAM',[345,430,450,459]),('KELLEMDERIEL',[96,556,228,582]),('THE KVA',[0,667,108,699]),("Zhethron's\nAerie",[60,721,120,746]),('Goldcrag',[121,750,169,766]),('SVORGALD',[410,768,519,853])],True,'核对原始地图地名；左边界另有截断的 Holklanda/Wretch Lands 字形片段，不据其他地图补写。')
    r[77]=([('THE TAWON\nEMPIRE',[718,15,1005,114]),('Beraza\nWoods\n(Contested\nTerritory)',[380,325,566,467]),('HOLKLANDA',[15,601,321,654]),('KELLEMDERIEL',[626,630,962,683])],False,'全尺寸地图可清晰读出四处文字；保留多行布局与括号。')
    r[90]=([('ABCDEFGHIJKLMNOPQRSTUVWXYZ',[0,0,283,17])],True,'这是位图字体图集：仅确认顶部完整大写字母序列；其余字形/标点不作为已读语句，字体资源应保留并另行适配中文。')
    r[97]=([('KHEMERIA',[401,222,710,284]),('THE WYLDRYLM',[465,550,855,611])],False,'查看原始近景地图，两个完整地名清楚可读。')
    r[99]=([('Buy',[3,54,37,71]),('Buy',[3,73,37,88]),('Combine',[52,91,104,108]),('G133',[478,588,519,608])],True,'UI 图集的 Buy/Combine 和底部资源标记可读；若干极小状态图标数字保留未决。G133 为资源标记，后续应禁翻。')
    save('dec6c25cd88d912fd36438105662111d1ebb366a5583ea6e395c3402c0aa9fc9',r,range(5,101))

def pack3():
    r={}
    r[22]=([],True,'全尺寸场景插画的药瓶标签和桌上地图有字形状标记，无法可靠判定/转写原文；不按 Qwen 的无字建议确认无字。')
    r[38]=([('Default attack buttons:',[3,0,153,15]),('Weapon',[24,115,82,131]),('Spell',[85,115,122,131])],False,'原图及清晰放大图显示教程标题与两个按钮说明。')
    r[48]=([('AVADON',[0,0,610,131]),('the BLACK FORTRESS',[7,129,602,202])],False,'核对大尺寸标题标志，与另一尺寸标志分别保留位置。')
    r[63]=([('THE FIVE NATIONS OF THE\nMIDLANDS PACT',[68,402,337,465]),('IN THE LANDS OF LYNAEUS',[80,477,278,498]),('6312',[291,477,324,498]),('KHEMERIA',[505,126,623,159]),('Dhorl\nStead',[465,169,498,193]),("Ogrhym'Tor",[516,171,579,193]),('THE WYLDRYLM',[414,475,598,506]),('Avadon',[625,474,684,497]),('THE CORRUPTION',[238,625,423,678]),('Contested\nTerritory',[582,611,640,641]),('THE TITAN PEAKS',[460,744,636,776]),('N',[96,836,123,864])],True,'查看原图并将小地名、日期、争夺地带放大核对；右边界残字及年代前的小符号保留未决，不补全。')
    texts=['Level','Experience','Next Level','Skills','Attributes','Health','Strength','Dexterity','Intelligence','Endurance','Vitality','Resistances','Armor:','Poison:','Magic:','Acid:','Fire:','Mental:','Cold:','Curses:','Specializations']
    boxes=[[25,16,67,33],[83,17,169,34],[188,17,273,34],[438,15,492,35],[47,83,130,102],[200,83,260,103],[30,112,97,130],[25,137,100,152],[21,158,108,177],[23,184,102,202],[192,156,266,176],[100,224,206,243],[30,255,90,273],[163,254,222,273],[32,281,91,299],[177,280,220,299],[49,305,89,323],[160,305,222,323],[47,329,91,349],[162,330,225,349],[88,370,245,390]]
    r[85]=(list(zip(texts,boxes)),False,'已查看全尺寸属性界面，逐项核对 21 处标签及冒号。')
    r[86]=([('Start New Game',[12,12,302,45]),('Load Game',[55,57,258,92]),('Instructions',[45,105,264,140]),('Settings',[79,151,238,190]),('Medals',[91,199,227,236]),('Quit',[112,246,195,283])],False,'已查看全尺寸主菜单，六项均清楚可读。')
    r[87]=([('Press these\nbuttons to\nuse items.',[7,23,144,87]),('Your Pack:',[179,4,285,26]),('1',[237,58,248,78]),('1',[237,101,249,120])],False,'教程说明、背包标题和两瓶药水旁的数字 1 清楚可见。')
    save('d7e6446003ada8ccf3374300a91b75a447995a9267b508677f436751686d1ea7',r,range(9,88))

if __name__=='__main__':
    globals()[sys.argv[1]]()
