"""PR141 attachment-led Metroidvania design film, not an implementation claim."""
from pathlib import Path
import argparse,copy,hashlib,json,math
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
HEAD='0e742706c59e3409b23c4536ba74f89af6a2146b'
COMMENT='https://github.com/zhipijun1996/gunman-rush/pull/141#issuecomment-6711181818'
ARCHIVES={
 'art':{'url':'https://github.com/user-attachments/files/34526011/godot-room-art-cloud.zip','sha256':'3d9d8a591a5a5672dbf81fd8feb487eed919d3897ee9ab02fa1c9559ebabc048','page_url':COMMENT},
 'world':{'url':'https://github.com/user-attachments/files/34526022/world-graybox-kit-v07-light-1.zip','sha256':'c4e6f7692bd3341aadf972f8c766a533fe39cea925c50694ad76ccfa32fdc395','page_url':COMMENT}}


def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,default=Path('/dev/shm/ep013'));a=p.parse_args();base=a.inputs
 art=base/'room-art/godot-room-art-cloud';world=base/'graybox/world-graybox-kit-v07'
 w=json.loads((world/'world-room-layout-v07.json').read_text());g=json.loads((world/'geometry-layout-v07.json').read_text())
 assert len(w['rooms'])==309 and len(w['regions'])==16
 assets=[]
 def member(id,archive,path,kind,label):
  prefix='godot-room-art-cloud/' if archive=='art' else 'world-graybox-kit-v07/'
  file=(art if archive=='art' else world)/path
  asset=dict(id=id,origin='archive',archive_id=archive,member=prefix+path,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
    preserve_evidence=True,kind=kind,display_label=label,pr=141,
    truth='Exact attachment member; design/assembly status retained. No import into main game and no claim of gameplay/physics validation.',
    rights='User requested use of owned project attachment. Art derivatives retain Asouris Underworld attribution; no CC0 claim.')
  assets.append(asset);return asset
 member('world','world','world-room-map-numbered-v07.png','world_design_map','世界结构规划 · 尚未完成实机')
 member('city','world','city-districts-v07.png','world_design_map','工城空间规划 · 非实机')
 member('sky','world','sky-trial-v07.png','world_design_map','天门路线规划 · 非实机')
 member('secrets','world','world-collection-secrets-v07.png','world_design_map','局部收集开发图 · 非玩家地图')
 ap='art/world-art-v2/'
 member('art-board','art',ap+'previews/regions-overview.png','art_assembly_preview','16区素材拼装预览 · 非正式关卡')
 member('plains','art',ap+'previews/windchime_plains-lit.png','art_assembly_preview','平原美术候选 · 素材拼装预览')
 member('forest','art',ap+'previews/thorn_forest-lit.png','art_assembly_preview','森林美术候选 · 素材拼装预览')
 member('mines-bg','art',ap+'assets/pixel/echo_mines-background.png','background_asset','矿井远景素材 · 非实机')
 member('five','art','.agents/skills/godot-room-art/assets/approved-five-regions.png','art_assembly_preview','已有美术方向 · 素材拼装预览')
 for id,path in [('clock-bg','assets/pixel/world_clock_heart-background.png'),('sky-bg','assets/pixel/starbridge_gate-background.png')]:
  if (art/ap/path).exists():member(id,'art',ap+path,'background_asset','区域远景素材 · 非实机')
 for id,path in [
  ('doc-start','START_HERE.txt'),('doc-status','handoff-status.json'),('doc-world','world-room-layout-v07.json'),
  ('doc-opening','design/OPENING_PACING-v07.txt'),('doc-station','design/STATION_NETWORK_STORY-v07.txt'),
  ('doc-city','design/CITY_SKY_WORLD-v07.txt'),('doc-contract','design/ROOM_CONSTRUCTION_README.txt'),
  ('doc-rules','design/world-graybox-bible-v04.txt'),('doc-collection','design/COLLECTION_LEVEL_DESIGN-v07.txt'),
  ('doc-font','assets/font-LICENSE.txt')]:member(id,'world',path,'source_document','附件设计原文')
 for id,path in [('doc-art-start','ROOM-ART-START.md'),('doc-art-readme',ap+'README.md'),('doc-art-provenance',ap+'asset-provenance.json'),('doc-art-checks','verification/summary.json')]:
  member(id,'art',path,'source_document','附件素材来源与范围')

 def text(x,y,value,size=44,color='#eef3fa',group=None,width=1700):
  e=dict(type='text',x=x,y=y,text=value,size=size,color=color,width=min(width,1850-x),bold=True)
  if group:e['group']=group
  return e
 def box(x,y,ww,hh,label,color,group=None):
  e=dict(type='rect',bounds=[x,y,ww,hh],fill='#182c3c',color=color,radius=16)
  if group:e['group']=group
  return [e,text(x+22,y+hh/2-23,label,42,color,group,ww-40)]
 # A selected logical diagram: connections match the actual station contract;
 # box sizes and arrows are editorial, never simulated world geometry.
 els=[text(105,210,'小站外面，很快就能自己选路',58),text(105,845,'分路说明图 · 按附件路网选取，非场景尺寸',28,'#a9b8c7')]
 els+=box(90,490,390,115,'钟外小站','#efd397')+box(650,490,530,115,'站外铃场','#89dfd1')
 els.append(dict(type='line',points=[[480,548],[650,548]],arrow=True,color='#89dfd1',width=6))
 choices=[('west',.08,1420,300,'西：果园与首Boss','#efd397'),('north',.32,1420,490,'北：塔脚与旧遗迹','#aab6ff'),('east',.56,1420,680,'东：田路与风车','#89dfd1')]
 groups=[]
 for id,start,x,y,label,color in choices:
  groups.append(dict(id=id,start=start,end=1,travel=.12,fade=.02,**{'from':[45,0],'to':[0,0]}))
  els+=box(x,y,450,115,label,color,id)
  els.append(dict(type='line',points=[[1180,548],[1290,548],[1290,y+58],[1420,y+58]],arrow=True,color=color,width=5,group=id))
 assets.append(dict(id='branch-diagram',origin='editorial',kind='explanatory_diagram',display_label='选路示意 · 非实机',
  graphic=dict(layout='diagram',background='#101b2b',elements=els,motion_groups=groups)))
 els=[text(105,210,'拿到新能力，再读一次旧地图',58),text(105,845,'钩索回访举例 · 设计路线示意',28,'#a9b8c7')]
 groups=[]
 for i,(xx,yy,title,detail,color) in enumerate([
  (110,350,'先看见','高处铜环与未到达的桥','#efd397'),
  (705,350,'取得钩索','新能力先解决眼前问题','#89dfd1'),
  (1300,350,'自己返回','桥通向新路线，也接回小站','#aab6ff')]):
  id='g'+str(i);groups.append(dict(id=id,start=.03+i*.24,end=1,travel=.12,fade=.02,**{'from':[0,45],'to':[0,0]}))
  els+=box(xx,yy,510,135,title,color,id)+[text(xx+18,yy+185,detail,34,'#eef3fa',id,490)]
  if i<2:els.append(dict(type='line',points=[[xx+510,yy+68],[xx+580,yy+68]],arrow=True,color=color,width=6,group=id))
 assets.append(dict(id='return-diagram',origin='editorial',kind='explanatory_diagram',display_label='能力回访说明 · 非实机',graphic=dict(layout='diagram',background='#101b2b',elements=els,motion_groups=groups)))

 # Exact raster viewports computed from the original plotting script's axes.
 rooms={r['id']:r for r in g['rooms']}
 def bounds(ids):
  pts=[pt for id in ids for pt in rooms[id]['polygon']]
  return min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)
 points=[pt for r in g['rooms'] for pt in r['polygon']]+[pt for e in g['connections'] for pt in e.get('polyline',[])]
 lim=[min(x for x,y in points)-38,min(y for x,y in points)-32,max(x for x,y in points)+38,max(y for x,y in points)+36]
 def crop(ids,pad=30,kind='world'):
  if kind=='world':
   width,height=5060,4015;ax=[.025,.10,.95,.73];l=lim
  else:
   code='G' if kind=='city' else 'V';bb=bounds([r['id'] for r in g['rooms'] if r['region']==code]);padding=85 if kind=='city' else 70
   l=[bb[0]-padding,bb[1]-padding,bb[2]+padding,bb[3]+padding]
   width,height=(4600,3450) if kind=='city' else (4600,2990);ax=[.035,.11 if kind=='city' else .12,.93,.67 if kind=='city' else .59]
  scale=min(width*ax[2]/(l[2]-l[0]),height*ax[3]/(l[3]-l[1]))
  ox=width*ax[0]+(width*ax[2]-(l[2]-l[0])*scale)/2
  oy=height*ax[1]+(height*ax[3]-(l[3]-l[1])*scale)/2
  bb=bounds(ids);x=max(0,math.floor(ox+(bb[0]-pad-l[0])*scale));y=max(0,math.floor(oy+(bb[1]-pad-l[1])*scale))
  right=min(width,math.ceil(ox+(bb[2]+pad-l[0])*scale));bottom=min(height,math.ceil(oy+(bb[3]+pad-l[1])*scale))
  return [x,y,right-x,bottom-y]
 regions=lambda codes:[r['id'] for r in g['rooms'] if r['region'] in codes]
 crops={
  'all':crop(regions([r['code'] for r in w['regions']]),14),
  'opening':crop(w['tutorial']['route'],35),
  'station':crop(['P-R01','P-R31','P-R32','P-R33','P-R34','P-R35'],30),
  'h-return':crop(['P-R14','P-R15','P-R32','P-R31','P-R01'],35),
  'plains':crop(regions(['P']),30),
  'forest-fungus':crop(regions(['F','M']),30),
  'city':crop(regions(['G']),35,'city'),
  'city-west':crop(['G-R01','G-R02','G-R13','G-R14','G-R17','G-R18','G-R19'],35,'city'),
  'city-east':crop(['G-R20','G-R21','G-R22','G-R23','G-R24','G-R14'],35,'city'),
  'city-upper':crop(['G-R28','G-R29','G-R30','G-R31','G-R32','G-R33','G-R08','G-R14'],35,'city'),
  'sky':crop(regions(['V']),30,'sky'),
  'sky-main':crop([f'V-R{i:02}' for i in range(1,11)],30,'sky'),
  'sky-extreme':crop([f'V-R{i:02}' for i in range(11,15)],30,'sky')}
 write(base/'research/crop-plan.json',crops)
 shots=[]
 def shot(title,narration,ids,ev,**kwargs):
  if isinstance(ids,str):ids=[ids]
  if isinstance(ev,str):ev=[ev]
  s=dict(id=f's{len(shots)+1:02}',chapter=str(len(shots)//4+1),title=title,narration=narration,assets=ids,
   offsets=[0]*len(ids),prs=[141],evidence=ev,transition='cut',shot_type='illustrated_design_explanation',
   fact_check='Exact attached v07/v2 source, scoped as design or independent Canvas assembly. No claim of completed309-room runtime, actual player tests or timings.',
   claim_type='documented_design_intent_with_editorial_first_person_narration',**kwargs)
  shots.append(s)
 def montage(title,voice,ids,ev,rects=None,**kwargs):
  shot(title,voice,ids,ev,presentation='montage',crop_rects=rects or [None]*len(ids),**kwargs)
 # Five approved Canvas scenes are640x360, spaced406px apart below34px labels.
 five=lambda i:[0,i*406+34,640,360]
 # Current sixteen-region contact sheet cells:320x180,30px header,10px row gap.
 tile=lambda i:[i%4*320,i//4*220+30,320,180]
 shot('工作量好像更大了','上一期我说，肉鸽随机可能得停一停。这次，我把世界规划到了三百零九个房间。工作量好像更大了。但我想先想清楚：玩家为什么往前走，又为什么愿意回来？','world','world',crop_rect=crops['all'],emphasis='刚想砍肉鸽，又画了309间房')
 montage('先看一眼新的方向','先放几张图。这些是现有素材拼出来的美术预览，地图则是新的世界设计。它们还没有变成一整款能玩的游戏，这次先聊我打算怎么做。',['five','five','art-board'],['art','world'],[five(0),five(1),[0,0,1280,870]],emphasis='设计与素材预览，先看方向')
 montage('围绕一个能记住的世界','这次想试试类银河恶魔城：一个固定、互相连通的世界。平原、森林、地穴，再到工城和天门，各有自己的位置与节奏。走过的地方，应该能慢慢变成玩家记得住的地方。',['world','world'],['world'],[crops['all'],crops['plains']],emphasis='类银河恶魔城 · 16个区域的相互联系')
 montage('世界钟心是远方目标','整个旅程围绕失准的世界钟心展开。先修各地的钟，寻找三枚核心，最后尝试重启钟心。这个目标，我希望玩家开局就能看见一个轮廓，旅途中再一点点理解。',['art-board','world'],['world','station'],[tile(15),crop(regions(['Z']),30)],emphasis='看得见远方，也知道为何出发')
 montage('开局先让人学会动作','开局先走过草坡、旧车厢、引渠和候车棚。走、跳、开枪，再练一次短反冲。失败以后，附近要有能重新站起来的地方。我不想刚进游戏，就让人补高难作业。',['plains','world'],['opening'],[None,crops['opening']],emphasis='先学会，再逐渐组合')
 shot('小站外就能选路','到了钟外小站，可以休息、看看服务，也可以直接出门。西边有果园和首个Boss，北边能去塔脚看旧遗迹，东边还有田路和风车。我想让人很快就有两个以上想去的地方。','branch-diagram',['opening','station'],presentation='animated_diagram',emphasis='先知道目标，然后自己选路')
 shot('让路网落到具体地方','图上这片，就是小站外的中央路网。下层有普通田路，上面留着暂时过不去的悬铃桥。小站旁边就有选择，回来的时候，也能认出熟悉的方向。','world',['station'],crop_rect=crops['station'],emphasis='钟外小站 → 站外分岔 → 塔脚／田路')
 montage('能力要带来重新发现','反冲仍然是动作基础。拿到钩索、墙面移动、二段跳以后，我希望变化能落在具体空间里：以前够不到的高处，突然有了走法。不是只在菜单里多一行说明。',['five','five'],['world','abilities'],[five(1),five(2)],emphasis='新能力，带来新走法')
 shot('新能力先解决眼前问题','比如拿到钩索之后，先用它完成一段眼前的路线，再从修钟后的回程，回到之前看见的悬铃桥。桥那头接着新方向，附近也有值得回来拿的东西。','return-diagram',['station','opening'],presentation='animated_diagram',emphasis='先看见 → 学会钩索 → 自己回来')
 montage('能力顺序保留选择','拿到钩索之后，还想保留两条能力路线：可以先往森林，找墙面能力；也可以去地穴这边，学二段跳。两种顺序都要能继续推进，后面也各有能回访的地方。',['five','five','world'],['abilities','world'],[five(1),five(2),crops['forest-fungus']],emphasis='先森林，还是先地穴？')
 shot('高处的门不是一张清单','能力阻隔也尽量放在房间内部。你能走进来，看见高台、墙面或另一头的落点，再判断现在能不能过去。以后带着新动作回来，最好还能想起自己第一次站在哪里。','world',['world','station'],crop_rect=crops['h-return'],emphasis='看到障碍，留下回来的念头')
 montage('一座城，要值得反复认识','工城这块，我想花更多心思。它被分成西街、广场、东城、动力沟、上层和授时院。第一次看到的窗、桥和高门，后面要真的能从另一面走到。',['five','city'],['city'],[five(3),crops['city']],emphasis='同一座工城，从不同方向认识')
 shot('第一次先认识生活街区','第一次从西街进城，先认识工房和武器匠。在广场看见对岸的住宅，也记住悬钟上方那扇暂时到不了的门。先让这座城，有一点生活的感觉。','city',['city'],crop_rect=crops['city-west'],emphasis='西街：先看见对岸与高门')
 shot('后来站到窗的另一面','后来从古堡或矿井绕进东城。先走一段没见过的街巷，再打开回西街的近路。这个时候回头看，我希望玩家能反应过来：原来对面那扇窗，是我之前看到的地方。','city',['city'],crop_rect=crops['city-east'],emphasis='东城：从窗的另一面回望')
 montage('再从高处认出旧街道','等熔火这边修复，再从维护通道进入钟体内部，走到上层，俯看原来经过的街道。条件够了可以接着探索，不会数着你来过几次，才肯开门。',['city','five'],['city'],[crops['city-upper'],five(3)],emphasis='上层：把记得的地方连起来')
 montage('收集物也要有获取过程','支路里也不能只摆个奖励，就算有探索了。先给一点线索，再让人观察、接近，完成一小段动作或遭遇。拿到东西之后，还要想好怎么回来，或者接到下一条路。',['world','five'],['collection'],[crops['station'],five(2)],emphasis='线索 → 挑战 → 奖励 → 回程')
 montage('死亡以后保留走过的成果','和上一期纠结的地方对应，这版规则会保留已拿到的能力、唯一成长和开通的捷径。地形失误，尽量在当前挑战附近重试；真正死亡才回休息点。这些还需要实机验证。',['city','plains'],['rules'],[crops['city-west'],None],emphasis='规划：成长与捷径永久保留')
 montage('时间失序也影响区域气质','美术这边，已经有十六区的素材拼装候选。平原的天光，森林的纵深，矿井和熔火的压迫感，会服务不同的路线和节奏。图好看只是开始，放进真实房间还得继续调。',['plains','forest','mines-bg','five'],['art'],[None,None,None,five(4)],emphasis='美术候选 · 还要服从真实房间')
 montage('别把整个世界做成高难走廊','我也不想把整个世界都做成连续跳跃考场。探索、普通遭遇、辨路和安静的小站，需要交替出现。钟修好了，灯光、声音和人物的近况，也能让回来这件事多一点意义。',['five','forest','plains'],['station','world'],[five(3),None,None],emphasis='紧张与放松，都要有位置')
 montage('给喜欢跳跳乐的人留一块地方','不过，我自己就喜欢连续精准操作的快感。所以天门还是想留一块后期平台挑战。左右两翼可以自己选顺序，学过的动作在这里重新组合，回程也要清楚。',['sky','art-board'],['sky','user-preference'],[crops['sky-main'],tile(14)],emphasis='天门：左右翼任选先后')
 shot('极限挑战不绑住所有人','更难的四间房，会放在独立极限支路。想挑战的人可以继续，主要成长和真结局不靠完成它来卡人。我想保留自己喜欢的难度，也给不同玩家留出选择。','sky',['sky'],crop_rect=crops['sky-extreme'],emphasis='高难可选，奖励不绑架主线')
 montage('图纸还要变成真正能玩的房间','现在完成的是世界关系、房间职责和一部分美术准备。图里的路线能解释通，不代表真实跳距、怪物配置、镜头和节奏就已经好玩。三百零九个房间，后面还得一间间做。',['world','art-board'],['limits','world','art'],[crops['all'],[0,0,1280,870]],emphasis='309间房是设计规模，还不是完成量')
 montage('下一步先把一小段做出来','下一步，先把开局、小站周围的回环，再加工城和天门的代表段，做成能操作的灰盒。看看那些想让人记住、想让人回来的地方，真正玩起来能不能成立。你们更想先看哪一块？',['plains','forest','five'],['limits','city','sky'],[None,None,five(3)],emphasis='先把一段做成好玩的，再继续铺开')

 spec=copy.deepcopy(json.loads((ROOT/'episodes/ep012.json').read_text()))
 spec.update(episode='ep013',repository='zhipijun1996/gunman-rush',asset_spec='episodes/ep013-assets.json',story_ids=['S_FIXED_WORLD_DESIGN'],
  title='刚想砍掉肉鸽，我又画了309间房 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】',
  title_candidates=['肉鸽先放一边，我想做一个值得回头的世界 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】'],
  shots=shots,rate='+8%',playback_speed=1.08,target_duration=[180,300],cover_assets=['plains','world'],
  cover={'series':'失序之钟 · 独游折腾记 ep12','left_label':'美术拼装预览','right_label':'世界设计图','line1':'刚想砍掉肉鸽','line2':'又画了309间房'},
  research_scope={'status':'targeted_PR_and_comment_attachment_research','pr':141,'repository':'zhipijun1996/gunman-rush','head_sha':HEAD,'merged':False,
   'coverage':'PR metadata/body, all3 conversation comments, no inline comments,20 changed-file names; both linked ZIPs inventoried and selected current design/source records read. Not a new full-history census.',
   'archives':ARCHIVES,'scope_limits':['PR body mentions20-room workline; attached v07 plan contains35 plains/309 world rooms. The newer attachment is the subject, not proof of integration.','ZIP internal dates differ by timezone/date; no invented chronology.','No code/import from attachment executed; main game remains untouched.']},
  evidence=[
   {'id':'pr141','kind':'unmerged_pull_request','repository':'zhipijun1996/gunman-rush','commit':HEAD,'pr':141,'url':'https://github.com/zhipijun1996/gunman-rush/pull/141','scope':'Documentation and skills, not full-world runtime delivery'},
   *[{'id':id,'kind':'exact_attachment_document','archive_id':'world','member':'world-graybox-kit-v07/'+path,'url':COMMENT,'scope':scope} for id,path,scope in [
    ('world','world-room-layout-v07.json','309 planned rooms,16 regions,411 connections; illustration coordinates are not physics'),
    ('opening','design/OPENING_PACING-v07.txt','Five tutorial rooms before station; timing budgets are targets, not playtest measurements'),
    ('station','design/STATION_NETWORK_STORY-v07.txt','Station west/north/east, visible grapple bridge, optional conversation, same-state returns'),
    ('abilities','world-room-layout-v07.json','H grapple first; W and D alternative orders; all obtain routes are proposals'),
    ('city','design/CITY_SKY_WORLD-v07.txt','36-room city, same landmark with different approaches; phase is not visit-count lock'),
    ('sky','design/CITY_SKY_WORLD-v07.txt','10 main/4 optional extreme; either wing order; extreme not true-ending requirement'),
    ('rules','design/world-graybox-bible-v04.txt','Permanent unique gains and shortcuts; nearby nonfatal terrain recovery vs actual death'),
    ('collection','design/COLLECTION_LEVEL_DESIGN-v07.txt','Authored clue/approach/challenge/acquisition/return; not actual player discovery tests'),
    ('limits','handoff-status.json','Structure graybox ready; no309-room Godot runtime, physics, combat balance or player-memory proof')]],
   {'id':'art','kind':'independent_canvas_assembly_and_assets','archive_id':'art','url':COMMENT,'member':'godot-room-art-cloud/art/world-art-v2/README.md','scope':'16 region material examples share study layout; not16 designed playable regions. v2 candidates vs five-region approved direction distinguished. Underworld/Asouris retained.'},
   {'id':'user-preference','kind':'user_testimony','scope':'User previously described liking Hollow Knight Path of Pain and consecutive precise platforming; this is not newly invented personal history.'}],
  comparison='Map and art preview show different kinds of design evidence, not before/after gameplay or equal-physics comparison.',
  comparison_review='美术图是否确实看得清；路线局部是否与解说一致；309房设计和正式实机有无混淆；新能力回访是否讲具体；美术示例不冒充城市地标已完成。',
  rights=[{'kind':'design_bundle','status':'User requested own project attachments; exact bytes retained'},
    {'kind':'art','status':'Project-derived/generated art with Underworld Tileset / Asouris original material; no blanket CC0 claim; bundle provenance retained'},
    {'kind':'voice','status':'Edge synthetic Mandarin, no voice cloning'},
    {'kind':'font','status':'New editorial text uses Noto CJK SIL OFL; original map raster font license retained from archive'},
    {'kind':'music','status':spec['music_asset']['license_status']}],
  bilibili_body='上一期还在纠结肉鸽随机，这次想试试类银河恶魔城的新方向，把固定世界设计摊开看看：16个区域、309个规划房间。\n\n从平原开局和钟外小站出发，讲讲能力回访、能自己选的路线、工城的不同入口，以及独立的天门高难支路。多放地图与现有美术拼装图，看看这个世界想让人记住什么。\n\n这是设计阶段记录。309间房不是已做完的实机关卡，美术图为独立素材拼装与候选表现，真实跳距、战斗、镜头和节奏还要一段段验证。\n\n中文AI配音；项目使用AI辅助开发与制作。地形基础素材：Underworld Tileset / Asouris；其余来源与派生记录保留。\n\n你们更想先看森林探索，还是天门跳跳乐？\n\n#B站AI创造公开赛# #独立游戏# #Godot# #失序之钟# #游戏开发#')
 write(ROOT/'episodes/ep013-assets.json',{'schema_version':2,'repository':spec['repository'],'archives':ARCHIVES,'assets':assets})
 write(ROOT/'episodes/ep013.json',spec)
 stories=json.loads((ROOT/'research/stories.json').read_text());stories=[s for s in stories if s['id']!='S_FIXED_WORLD_DESIGN']
 stories.append({'id':'S_FIXED_WORLD_DESIGN','event':'从随机拼装转向固定世界：309房的能力回访与城市空间发现','date':'2026-11-07',
  'background':'Previous episode questioned random roguelike fit; user asks to explain new Metroidvania design from PR141 ZIPs.',
  'conflict':'Map size and coherent specification still do not prove fun; spatial memory and meaningful return must survive real level construction.',
  'attempts':['16-region/309-room plan','Station branching and grapple revisit','Same city landmark revealed from several approaches','Optional extreme platforming distinct from main progression','Layered region art study'],
  'result':'Design and source-material delivery; not full-game implementation','commit':HEAD,'base_commit':'d04912228d6f53f61bd6dde84b22876a5d444487','pr':141,'branch':'feat/plains-design-skill',
  'sources':[{'url':COMMENT,'archives':ARCHIVES}],
  'media':['world','city','sky','plains','forest','five','art-board'],
  'truth_status':'planned_and_independent_assembly_preview','evidence_status':'Exact attachment SHA/member hashes and actual diagrams inspected; unmerged PR boundary retained.',
  'recordability':{'source_available':True,'saved_media_available':True,'historical_rebuild':'Not needed; video uses design drawings and actual saved Canvas previews, not game footage.'},
  'video_potential':{'priority':'high','reason':'Direct continuation with concrete branching, revisits and memorable city; visually rich source bundles.'}})
 write(ROOT/'research/stories.json',stories)
 print('Authored',len(shots),'shots,',len(assets),'assets; narration chars',sum(len(s['narration']) for s in shots))


if __name__=='__main__':main()
