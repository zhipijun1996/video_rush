"""Extend ep12 from a design introduction to the first PR142 implementation attempts."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def main():
    spec=read('episodes/ep013-r2.json');assets=read(spec['asset_spec']);packet=read('research/pr142-episode-sources.json')
    old={s['id']:s for s in spec['shots']};all_map=old['r2s02']['crop_rect']
    new=[]
    def external(id,url,sha,kind,label,**extra):
        new.append(dict(id=id,origin='external',url=url,sha256=sha,kind=kind,display_label=label,pr=142,
                        page_url=packet['url'],rights='User-owned project recording/design; original third-party art attribution retained.',**extra))
    for x in packet['clips']:
        external(x['id'],x['url'],x['sha256'],'original_game_recording','当前返工版 · 原始录屏／局部起点',
                 runtime_commit=x['source_commit'],truth=x['scope'],source_build='e0da5f93cf15')
    for x in packet['room_screenshots']:
        external(x['id'],x['url'],x['sha256'],'positioned_game_screenshot','当前返工版 · 实机定位图',
                 runtime_commit='ae5c1cca26192788733bb733f5ba19e0ad48c5fb',truth='Original source-provided positioned screenshot. Not proof of traversal or completed region.')
    for id in ['map','outline']:
        x=packet[id];external('plains-'+id,x['url'],x['sha256'],'world_design_map','平原施工总图 · 含未完成房间',truth='04 room footprints; only the initial six interiors currently loaded.')
    native={'id':'new-intro','origin':'world_recording','repository':packet['repository'],'commit':packet['head'],
            'case':'pr142-intro-map','kind':'historical_reconstruction','pr':142,
            'display_label':'当前开发版 · 新录屏／自动输入',
            'truth':'New native recording of frozen draft PR142, using original route helpers/controller and an isolated save. No position/health/progress writes; not a full playthrough or human playtest.',
            'rights':'User-owned game; original project and Underworld / Asouris asset notices retained.'}
    new.append(native)
    for id,t in [('new-map',10.5),('door-frame',8.2)]:
        x=copy.deepcopy(native);x.update(id=id,frame_seconds=t,kind='original_game_screenshot',display_label='当前开发版 · 新录屏抽帧');new.append(x)
    loop=copy.deepcopy(next(a for a in assets['assets'] if a['id']=='idea-loop'))
    manual=copy.deepcopy(loop);manual.update(id='room-loop',display_label='逐房设计 · 下一步思路示意')
    replace={'成长，也是在重新认识世界':'一间房，要把什么体验做好？','看见障碍':'看懂下一步','记住一个暂时去不了的地方':'先看清落点、出口和线索',
             '学到新动作':'操作与选择','多了一种解决问题的方法':'反冲、战斗、探索要有意义','回来发现新路':'失败也回得来','旧地方，也有了新的意义':'能重试，也能留下新的发现'}
    for e in manual['graphic']['elements']:
        if e.get('text') in replace:e['text']=replace[e['text']]
    new.extend([manual,{'id':'first-rejected','origin':'editorial','kind':'editorial_quote','pr':142,
      'display_label':'早期版本结论 · 开发记录摘述',
      'truth':'Editorial typesetting of a verified historical document, not a screenshot or footage of the first version.',
      'graphic':{'kicker':'第一版房内关卡 · 体验返工','face':'thinking','lines':['运行接入 ≠ 内容完成','整体质量结论：返工'],
                 'font_size':66,'footer':'开发记录摘述 · 当前实机另行标注'},'rights':'Original editorial layout; wording verified in pinned withdrawal document.'}])
    shots=[]
    def shot(title,text,ids,evidence,**extra):
        if isinstance(ids,str):ids=[ids]
        x=dict(id=f'r3s{len(shots)+1:02}',chapter=str(len(shots)//4+1),title=title,narration=text,assets=ids,offsets=[0]*len(ids),
               prs=[142],evidence=['user-pr142',*evidence],transition='cut',shot_type='design_thinking_and_actual_first_attempts',
               claim_type='first_person_reflection_and_scoped_draft_implementation',
               fact_check='Intent/dissatisfaction from user testimony; implementation bounded to pinned PR142. Current repair footage is not labelled the rejected first version. Planned world/art not represented as completed gameplay.')
        x.update(extra)
        if len(ids)>1 and 'presentation' not in extra:x.update(presentation='montage')
        shots.append(x)
    shot('开始做，也开始踩坑','类银河恶魔城，启动！这次不光画地图，开始往游戏里做了。然后我发现，图上想得挺好，真跑起来，坑还不少。',
         ['new-intro','world'],['pr142-scope'],montage_weights=[.8,.2],crop_rects=[None,all_map],emphasis='类银河恶魔城，启动！')
    shot('为什么换方向','之前折腾随机地图，是想让每一局都有点新鲜感。但我的核心是反冲跳跃，我更想做的，其实是学会一个动作，再跨过原来过不去的地方。',
         ['world','plains'],['user-preference','world'],crop_rects=[all_map,None],emphasis='围着反冲跳跃，重新想地图')
    shot('想要怎样的探索','所以这次试试固定世界。先看到一个去不了的地方，记在心里。后来有了新能力，自己回来找到新路。成长能留下来，旧地方也能有新的意思。',
         'idea-loop',['world','abilities'],presentation='animated_diagram',emphasis='新能力，改变你看地图的方式')
    shot('回头也有发现','比如工城，我希望先看见远处的窗和高处的桥。以后绕回来，认出自己来时的街道，发现原来都连着。想做的是这种探索感。',
         ['five','city'],['city'],crop_rects=[[0,3*406+34,640,360],old['r2s09']['crop_rects'][0]],emphasis='回到旧地方，也像一次新探索')
    shot('先搭起基础','想法有了，就先把底子搭起来。房间和能力怎么连，成长怎么保留，休息和失败后从哪里重新出发。先让这些规则在游戏里有个着落，再慢慢往里填内容。',
         ['world','P-R01'],['pr142-state'],crop_rects=[all_map,None],emphasis='先让世界有个能运行的底子')
    shot('AI第一版，我不满意','最先撞墙的就是房内关卡。AI做出来的第一版，我完全不满意。图里写了这间房要练什么，不代表摆出来的台子，就真的能让玩家玩到那个东西。',
         ['first-rejected','plains-map'],['withdrawal','pr142-scope'],montage_weights=[.45,.55],emphasis='写清了职责，还不等于做好了关卡')
    shot('要看实际怎么玩','不光是能不能跳过去。起跳前看不看得见落点？走错了能不能回来？一段操作之后，有没有继续往前走的欲望？这些得进游戏里，一段段看。',
         ['carriage','recovery','P-R22'],['saved-clips','pr142-scope'],montage_weights=[.34,.31,.35],emphasis='能通关，只是开始')
    shot('先把房间口接起来','房间口也踩了坑。现在尝试在真实墙面上留缺口，侧面走过去，上下靠跳跃或者下落接起来。不能只在地图上画条线，实地却看不懂往哪走。',
         ['new-intro','door-frame','plains-outline'],['pr142-doors','new-native'],offsets=[7.2,0,0],montage_weights=[.13,.37,.50],emphasis='地图上的连接，要落到真正的出口')
    shot('镜头也是关卡的一部分','镜头也得一起考虑。出口在哪、下一步往哪落，要在操作前让人看见。最近还在改这些最基础的东西。以前觉得只是接个房间，现在发现真没那么简单。',
         ['shelter','P-R24'],['saved-clips','pr142-scope'],montage_weights=[.36,.64],emphasis='先看得懂，才能放心操作')
    shot('地图和实际空间对上','大地图这边，尝试让房形、房间口和地图用同一套空间数据。走过的地方再显示出来。至少希望玩家看着地图，能跟自己刚刚走过的路对上。',
         ['new-intro','plains-map'],['pr142-map','new-native'],offsets=[9.1,0],montage_weights=[.25,.75],emphasis='地图，要对应脚下真正走过的路')
    shot('先做一小段','这张是目前平原的施工总图。但有整区图，不等于整区能玩。现在先盯开头这一小段，其余房间继续改，先别急着给自己发完工证。',
         ['plains-map','P-R03'],['pr142-scope'],emphasis='整区图，不是整区完工')
    shot('当前的局部尝试','从草坡出发，过车厢、引渠，再走到小站。这里先把走跳、射击、反冲和歇脚的地方接起来。眼前这些，都还是返工中的片段。',
         ['new-intro','station'],['saved-clips','new-native','pr142-scope'],offsets=[13.1,0],montage_weights=[.60,.40],emphasis='当前实机 · 仍在返工')
    shot('几段修复，不等于好玩了','修掉几个盲跳、补上失误后的回路，当然要做。但这不等于关卡就好玩了。房间之间怎么铺垫、怎么变化、回来的时候还有没有意思，都还得继续试。',
         ['new-intro','P-R23'],['pr142-scope','new-native'],offsets=[25.7,0],montage_weights=[.68,.32],emphasis='修掉问题，还要继续找乐趣')
    shot('后面得我自己设计','所以后面不能指望AI把房间批量铺完就行。每间房想让人看见什么、尝试什么、怎么失败再回来，我得自己先设计、先判断，再让AI帮忙落地。',
         'room-loop',['user-pr142','pr142-scope'],presentation='animated_diagram',emphasis='房内玩法，需要继续人工设计')
    shot('把节奏也做出来','反冲跳跃还是核心，但也不能整张地图都绷着。战斗、观察、探索和休息，得有松有紧。难一点的路线可以留着，也想给玩家一点自己选择的空间。',
         ['plains','forest','five'],['user-preference','world'],crop_rects=[None,None,[0,34,640,360]],emphasis='跳得爽，也得有探索和喘息')
    shot('三百多个，慢慢来','一想到整张世界图，工作量确实有点顶。也就三百多个房间，慢慢来。先把眼前这几间做明白，比一口气铺满更重要。',
         'world',['world','user-pr142'],crop_rect=all_map,safe_frame=True,emphasis='也就三百多个房间，慢慢来')
    shot('画面也还要磨','画面也一样。漂亮的素材和方向图，放进真正的房间，不会自动变成舒服的游戏画面。地形、视野、角色和环境层次，还得放在一起反复磨。',
         ['forest','P-R03','P-R01'],['art','pr142-scope'],emphasis='方向图到实际游戏，还有很长一段路')
    shot('先用一段能玩的来检验','接下来就先做一小段，看看动作和路线能不能真的连出乐趣。不好玩的地方，该推翻还得推翻。我开始尝试做类银了，但路还很远，坑也不少。',
         ['P-R21','plains-map'],['pr142-scope','user-pr142'],emphasis='先做一段，再判断方向')
    shot('先往下试试','现在的效果还没到自己满意的程度。大家有什么关卡设计的建议，也欢迎告诉我。不知道能不能做好，先往下试试。',
         ['P-R03','plains'],['user-pr142','limits'],emphasis='不知道能不能做好，先往下试试')
    spec.update(episode='ep013-r3',asset_spec='episodes/ep013-r3-assets.json',shots=shots,
        title='类银河恶魔城，启动！开始做了，也开始踩坑了 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】',
        title_candidates=['类银计划，启动！AI做的第一版关卡，我完全不满意 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】'],
        cover_assets=['P-R03','world'],cover={'series':'失序之钟 · 独游折腾记 ep12','left_label':'当前开发实机','right_label':'大世界规划','line1':'类银河恶魔城','line2':'启动！先试试'},
        comparison='Early rejection is a sourced editorial card. Current repair footage is labelled separately; art references and planned maps are not matched gameplay comparisons.',
        comparison_review='是否看懂转向思路、第一版体验不满意和后续人工设计；当前修复片段是否被误读为旧版或整区完成；原生跨房与地图是否清楚；三百多房只作工作量自嘲；末尾仍保留不确定。',
        bilibili_body='类银河恶魔城，启动！这次开始把想法往游戏里做，也开始踩新的坑。\n\n先聊聊为什么转向固定世界，想怎样用新能力、回访和路线选择做探索；再看看开头关卡、房间口和大地图的实际尝试。AI做的第一版房内关卡，我完全不满意。后面需要自己继续设计和判断，再让AI帮忙落地。也就三百多个房间，慢慢来。\n\n目前只在做开头的一小段，施工图不代表整区已能玩，当前录屏也不是质量验收通过。房内玩法、回访、镜头和画面还在打磨。路还很远，现在效果也不好，不知道能不能做好，先往下试试。\n\n中文AI配音，含真实游戏录屏、定位截图、规划图及明确标注的示意图。部分原始录屏从指定局部起点自动操作；新录片段使用正常新档和原控制器。AI辅助开发与制作。地形基础素材：Underworld Tileset / Asouris。\n\n#B站AI创造公开赛# #独立游戏# #类银河恶魔城# #Godot# #失序之钟#')
    spec['evidence'].extend([
      {'id':'user-pr142','kind':'user_testimony_and_editorial_request','text':'AI first room interiors completely unsatisfactory; continue manual design, 300+ rooms slowly. Began trying Metroidvania; still poor, many pitfalls and a long road. Add actual recording; not an upload request.'},
      *[{'id':id,'kind':'pinned_repository_evidence','commit':packet['head'],'pr':142,'text':text} for id,text in {
        'pr142-state':'Current state: fixed-world basics, permanent growth, rest and separate draft scope.',
        'pr142-scope':'First six current interiors, 29 remain; prior quality acceptance withdrawn; pre-action visibility/recovery and full quality remain distinct.',
        'pr142-doors':'Actual boundary apertures and directional crossings; shared player, per-room camera, not an entirely loaded seamless world.',
        'pr142-map':'WorldMap uses actual footprint union/shared doorway data, normal map shows explored rooms.',
        'saved-clips':'Four original native local-start recordings match all byte lengths and SHA256 in current-checks.json.',
        'new-native':'Fresh frozen-PR142 native recording: source route helpers/controller, new-game crossing and explored map, no direct player/progress writes.'}.items()],
      {'id':'withdrawal','kind':'historical_quality_rejection','commit':'8e88b93e8f4c0db6c023084abc6710e5ef766ab1','pr':142,'text':'Actual current_state.md states 整体质量结论为返工 and 运行接入不等于内容完成. Card is editorial typesetting.'}])
    spec['research_scope'].update(pr142_head=packet['head'],pr142_base=packet['base'],pr142_commits_read=len(packet['commits']),pr142_changed_paths=1068,pr142_comments=0,
        editorial_revision='Design intent plus actual first implementation attempts. Draft PR142, quality unaccepted, source runtime untouched.')
    assets['assets']+=new
    used={i for s in shots for i in s['assets']}
    assets['assets']=[a for a in assets['assets'] if a['id'] in used or a.get('kind')=='source_document']
    assets['documents']=packet['documents']
    save('episodes/ep013-r3-assets.json',assets);save('episodes/ep013-r3.json',spec)
    print(len(shots),'shots;',sum(len(s['narration']) for s in shots),'narration characters')

if __name__=='__main__':main()
