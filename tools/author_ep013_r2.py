"""Re-edit ep12 around design thinking, retaining the exact PR141 evidence."""
import copy,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    original=json.loads((ROOT/'episodes/ep013.json').read_text())
    old_assets=json.loads((ROOT/original['asset_spec']).read_text())
    old={s['id']:s for s in original['shots']}
    all_map=old['s01']['crop_rect']
    plains_map=old['s03']['crop_rects'][1]
    station=old['s07']['crop_rect']
    city=old['s12']['crop_rects'][1]
    city_west=old['s13']['crop_rect'];city_east=old['s14']['crop_rect'];city_upper=old['s15']['crop_rects'][0]
    sky=old['s20']['crop_rects'][0]
    five=lambda i:[0,i*406+34,640,360]
    tile=lambda i:[i%4*320,i//4*220+30,320,180]
    loop=copy.deepcopy(next(x for x in old_assets['assets'] if x['id']=='return-diagram'))
    loop.update(id='idea-loop',display_label='成长与回访 · 设计思路示意')
    replacements={
        '拿到新能力，再读一次旧地图':'成长，也是在重新认识世界',
        '钩索回访举例 · 设计路线示意':'设计思路示意 · 非实机',
        '先看见':'看见障碍','高处铜环与未到达的桥':'记住一个暂时去不了的地方',
        '取得钩索':'学到新动作','新能力先解决眼前问题':'多了一种解决问题的方法',
        '自己返回':'回来发现新路','桥通向新路线，也接回小站':'旧地方，也有了新的意义'}
    for e in loop['graphic']['elements']:
        if e.get('text') in replacements:e['text']=replacements[e['text']]
    for g,start in zip(loop['graphic']['motion_groups'],[.02,.24,.43]):g['start']=start
    shots=[]
    def shot(title,voice,assets,evidence,rect=None,rects=None,montage=False,diagram=False,**kwargs):
        if isinstance(assets,str):assets=[assets]
        if isinstance(evidence,str):evidence=[evidence]
        x={'id':f'r2s{len(shots)+1:02}','chapter':str(len(shots)//4+1),'title':title,'narration':voice,
           'assets':assets,'offsets':[0]*len(assets),'prs':[141],
           'evidence':['user-r2',*evidence],'transition':'cut','shot_type':'illustrated_personal_design_thinking',
           'claim_type':'personal_design_intent_with_pinned_attachment_examples',
           'fact_check':'First-person aims are an editorial synthesis of user steering and PR141 design documents. No new runtime, player feedback, completed world or guaranteed success is claimed.',**kwargs}
        if montage:x.update(presentation='montage',crop_rects=rects or [None]*len(assets))
        elif diagram:x['presentation']='animated_diagram'
        elif rect is not None:x['crop_rect']=rect
        shots.append(x)
    shot('类银河恶魔城，启动','肉鸽随机先放一边。这次，我想把失序之钟往类银河恶魔城的方向试一试。类银河恶魔城，启动！',
         ['forest','five','world'],['world','art'],montage=True,rects=[None,five(3),all_map],emphasis='类银河恶魔城，启动！')
    shot('为什么想换一个方向','之前一直在想，地图每局都换，会不会更耐玩。但我最在意的，其实是学会一个动作，再用它跨过之前过不去的地方。现在想先围着这个乐趣来设计世界。',
         'world',['world','user-preference'],rect=all_map,safe_frame=True,emphasis='围着反冲跳跃的乐趣，重新想地图')
    shot('想要一个能熟悉的世界','这回我想要的，是一个能逐渐熟悉的世界。第一次经过只是看看风景，后来学会新能力，再回来发现：原来这里还有一条路。',
         ['plains','world'],['world','station'],montage=True,rects=[None,station],emphasis='走过的地方，慢慢变得熟悉')
    shot('成长要能被感到','先看见一个去不了的地方。学会新能力。再自己回来，找到新的路。我想让成长体现在操作和发现里，真的感觉自己比第一次更自由。',
         'idea-loop',['abilities','station'],diagram=True,emphasis='新能力，改变你看地图的方式')
    shot('留下一点想回来的念头','障碍也想让玩家看得明白。能看见远处的平台，试过一两次，大概知道自己还缺什么。以后回来，那种这次我能过去了的感觉，才有分量。',
         ['five','forest'],['abilities','station'],montage=True,rects=[five(0),None],emphasis='这次过不去，也记住了这个地方')
    shot('给自己选路的理由','路线也希望留点选择。看到一个分岔，能因为地形、远景或者一点线索，自己决定往哪走。我不想让探索最后变成对着任务列表打勾。',
         ['world','world'],['world','station'],montage=True,rects=[plains_map,station],emphasis='选路，要有自己的理由')
    shot('绕过去的过程也要有意思','当然，岔路多不一定就好玩。支路得有能记住的发现，绕过去的过程也得有意思。奖励只是其中一部分，我还想把看见、想去、试一试、再回来的过程连起来。',
         ['five','world'],['collection','station'],montage=True,rects=[five(2),station],emphasis='发现的乐趣，也在到达的过程里')
    shot('用一座城市举个例子','工城我就想试试这样的做法。第一次在广场上，看见对岸的窗和高处的桥。先不用把它们全走到，只要留下一个印象。',
         ['five','city'],['city'],montage=True,rects=[five(3),city_west],emphasis='先看见一个想去的地方')
    shot('回头也能是新的探索','以后从别的方向绕回来，站到那扇窗后面，再从高处认出自己来时的街道。我想要这种原来都连在一起的发现感，让返回旧地方也像一次探索。',
         ['city','city','five'],['city'],montage=True,rects=[city_east,city_upper,five(3)],emphasis='原来，它们都连在一起')
    shot('熟悉的路也可以变轻松','捷径也是同一个思路。第一次有一点绕，有一点紧张；等路打开，再经过就轻松一些。地图逐渐熟悉，玩家也能感觉到，自己确实改变了这个地方。',
         ['city','plains'],['city','rules'],montage=True,rects=[city,None],emphasis='打开一条路，也留下了一点改变')
    shot('让探索有一点积累','和之前纠结的肉鸽相比，这次更想让探索有积累。学到的能力、拿到的成长、开过的路，都留下来。失败当然还是会有代价，但不想让重新出发只剩重复。',
         ['world','five'],['rules'],montage=True,rects=[station,five(0)],emphasis='失败之后，也留下走过的成果')
    shot('节奏需要有松有紧','反冲跳跃还是游戏的核心。不过，整张地图都做成高难跳跃，我自己想想也累。战斗、探索、观察和安静的小站，需要有松有紧地穿插。',
         ['plains','forest','five'],['world','station'],montage=True,rects=[None,None,five(0)],emphasis='紧张之后，也能喘口气')
    shot('把难度也变成一种选择','我喜欢连续精准操作的快感，这部分会留给愿意挑战的人。难一点的路线可以很爽，但我不想把每个玩家都堵在那里。想多探索和想挑战极限，尽量都能有选择。',
         ['sky','art-board'],['sky','user-preference'],montage=True,rects=[sky,tile(14)],emphasis='探索和高难挑战，都想保留')
    shot('区域要能被记住','区域也要能被记住。平原的开阔、森林的遮挡、工城的生活痕迹，不能只停在一张漂亮的背景上。画面、路线和经过这里的感觉，最好能一起形成印象。',
         ['plains','forest','five'],['art','city'],montage=True,rects=[None,None,five(3)],emphasis='画面、路线和感受，形成同一个印象')
    shot('故事放在旅途里','失序之钟这个名字，也想在旅途中慢慢讲出来。看见失准的钟，经过还在生活的小站，再看着一些地方重新有了回应。故事尽量长在环境里，别一直拦着玩家听我讲。',
         ['art-board','plains','mines-bg'],['world','station','art'],montage=True,rects=[tile(15),None,None],emphasis='在环境里，慢慢认识这个世界')
    shot('现在还只是想做的方向','现在这些图，是我想做的方向，不是游戏已经变成这样了。规划能讲通，离真正玩起来有意思，还差着房间、动作、怪物、镜头这些实际工作。',
         ['art-board','world'],['limits','art'],montage=True,rects=[[0,0,1280,870],all_map],emphasis='这些图是方向，游戏还得继续做')
    shot('先用一小段来检验','接下来先做一小段，看看新能力和旧路线能不能真的产生联系，关卡玩起来有没有节奏。好用的再往下做，别急着因为地图画得大，就觉得方向已经选对了。',
         ['forest','five'],['limits'],montage=True,rects=[None,five(0)],emphasis='先做一段，检验想法')
    shot('先往下试试','想法先放在这里。大家有喜欢的类银设计，也欢迎给我点建议。接下来该改就改，不知道能不能做好，先往下试试。',
         'plains',['limits'],safe_frame=True,emphasis='不知道能不能做好，先往下试试')

    spec=copy.deepcopy(original)
    spec.update(episode='ep013-r2',asset_spec='episodes/ep013-r2-assets.json',
        title='类银河恶魔城，启动！我想做个值得回头的世界 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】',
        title_candidates=['类银计划，启动！这次想把探索做得更有意思 | 【失序之钟】独游折腾记 ep12【B站AI创造公开赛】'],
        shots=shots,rate='+5%',playback_speed=1.02,target_duration=[180,300],cover_assets=['forest','world'],
        cover={'series':'失序之钟 · 独游折腾记 ep12','left_label':'美术方向预览','right_label':'探索世界规划','line1':'类银河恶魔城','line2':'启动！'},
        comparison_review='是否以动机、取舍和玩家感受为主；工城只作一个简短例子；没有逐项介绍房号、入口条件、数量或能力顺序；最后明确仍不确定能否做好。',
        bilibili_body='肉鸽随机先放一边，这次想往类银河恶魔城的方向试一试。\n\n想做一个能逐渐熟悉，又能随着新能力发现新路线的世界。聊聊为什么想换方向，怎样让探索和成长留下积累，以及怎样让回到旧地方也有新的意思。反冲跳跃仍然是核心，探索、战斗、放松和高难挑战之间，也想找到合适的节奏。\n\n图里的世界目前是设计与美术方向，不是正式游戏已经变成这样了。接下来先做一小段能玩的关卡，看看想法能不能成立。不知道能不能做好，先往下试试。\n\n中文AI配音；地图为规划图，美术为独立素材拼装预览。项目使用AI辅助开发与制作。地形基础素材：Underworld Tileset / Asouris。\n\n#B站AI创造公开赛# #独立游戏# #类银河恶魔城# #Godot# #失序之钟#')
    spec['evidence'].append({'id':'user-r2','kind':'user_editorial_steering','text':'Reduce specific detail and focus on design thinking. Title should evoke Metroidvania and use 启动. Explicit uncertainty and willingness to keep trying; not a request to upload.'})
    spec['research_scope']['editorial_revision']='Same frozen PR141 archives; ideas and intended player experience instead of counts/room walkthrough. No new game implementation claim.'
    used={id for s in shots for id in s['assets']}
    assets=copy.deepcopy(old_assets)
    assets['assets']=[x for x in assets['assets'] if x['origin']=='archive' and (x['id'] in used or x['kind']=='source_document')]+[loop]
    write(ROOT/'episodes/ep013-r2-assets.json',assets)
    write(ROOT/'episodes/ep013-r2.json',spec)
    print('Authored',len(shots),'shots,',sum(len(s['narration']) for s in shots),'narration characters;',len(assets['assets']),'assets')


if __name__=='__main__':main()
