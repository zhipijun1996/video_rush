"""Author ep11: real module/map evidence and the developer's tentative pivot.

No external project is edited. All screenshots are reconstructed from frozen
commits by the ordinary browser_capture adapter; no fabricated gameplay.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
EDIT = '06bae30acb9709a24559c8ada532618be8500cac'
GEN = 'b15c32e045347e0fcf282d541ea3eaa4661f0835'


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map-gen',type=Path,required=True)
    p.add_argument('--map-edit',type=Path,required=True)
    p.add_argument('--region-image',type=Path,required=True)
    a=p.parse_args()
    assets=[]
    paths=sorted(x.name for x in a.map_edit.iterdir() if x.is_file())+['modules','generation/module-workshop']
    library=[{'operation':'click','selector':'#library'},
             {'operation':'wait','selector':'.module-card','first':True}]
    def browser(id, steps, entry='index.html', caption='模块库网页 · 固定源码重现'):
        assets.append(dict(id=id,origin='browser_capture',commit=EDIT,
            snapshot_paths=paths,entry=entry,steps=steps,kind='web_editor_evidence',
            caption=caption,truth='New capture of exact committed web tool; no server writes; route drawings are design annotations, not physics or fun acceptance',
            rights='User-owned project; requested quotation of project interface'))
    browser('catalog',library)
    browser('catalog-forest',library+[{'operation':'select','selector':'#library-category','value':'森林'}])
    ids=['b31-n06-fourport-two-low-ingress','b31-n08-reward-return-interface0','b31-n12-three-side-port-interface0']
    for i,id in enumerate(ids):
        browser('module'+str(i),library+[
            {'operation':'click','selector':f'[data-copy-module="{id}"]'},
            {'operation':'wait','selector':'#dialog','state':'hidden'}])
    for id, path in [
        ('map-a','experiments/optimization-v2/output/figures/validation-930001.png'),
        ('map-b','experiments/optimization-v2/output/figures/calibration-271028.png'),
        ('map-c','experiments/optimization-v2/output/figures/validation-930012.png'),
        ('seal','experiments/legacy-real-v2/output/gear-seal-detail.png'),
        ('early','experiments/optimization-v1/output/comparison-browser.png')]:
        file=a.map_gen/path
        url=f'https://raw.githubusercontent.com/zhipijun1996/map-gen/{GEN}/{path}'
        assets.append(dict(id=id,origin='external',url=url,
            page_url=f'https://github.com/zhipijun1996/map-gen/blob/{GEN}/{path}',
            repository='zhipijun1996/map-gen',commit=GEN,path=path,
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),kind='archived_algorithm_comparison',
            caption='真实实验存档 · 静态路线，非实机验收',
            truth='Unmodified archived output. Four panels share seed, module package and drawing scale; geometry targets do not establish whole-map physics or player fun.',
            rights='User-owned project; requested experimental evidence'))
    target=ROOT/'build/inputs/ep012-region-plan.jpg';target.parent.mkdir(parents=True,exist_ok=True)
    if target.resolve()!=a.region_image.resolve():shutil.copyfile(a.region_image,target)
    assets.append(dict(id='plan',origin='user_upload',path=str(target.relative_to(ROOT)),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),kind='planned_world_map',
        original_filename='1000062461.jpg',user_attachment=True,
        caption='区域规划草案 · 尚未实现',
        truth='Planning image, not runtime or a committed implementation decision',rights='User supplied for this episode'))

    def text(x,y,t,size=52,color='#eef3fa',group=None):
        e=dict(type='text',x=x,y=y,text=t,size=size,color=color,width=1700-x,bold=True)
        if group:e['group']=group
        return e
    def diagram(id,title,rows,footer='个人复盘 · 思路示意'):
        # Keep diagram headings below the separate ASS emphasis line at y120.
        elements=[text(110,210,title,60),text(110,835,footer,28,'#a9b8c7')]
        groups=[]
        for i,(label,detail,color) in enumerate(rows):
            name='g'+str(i);y=295+i*155
            groups.append(dict(id=name,start=.05+i*.19,end=1,travel=.12,fade=.02,**{'from':[90,0],'to':[0,0]}))
            elements += [dict(type='rect',bounds=[110,y,1700,125],fill='#192e43',color=color,group=name),
                         text(150,y+22,label,44,color,name),text(730,y+31,detail,34,'#eef3fa',name)]
        assets.append(dict(id=id,origin='editorial',kind='explanatory_diagram',
            caption=footer,truth='Original animated explanation of user testimony, not a measured player study',
            graphic=dict(layout='diagram',background='#101b2b',elements=elements,motion_groups=groups)))
    diagram('hook','做了一百多个模块以后……',[
        ('原计划：随机生成','省一点关卡设计','#89e6cc'),
        ('现在：模块还得继续做','新鲜感，没那么容易','#ffd98c'),
        ('我开始怀疑这条路','是不是该换个方向？','#ff9d9a')])
    diagram('questions','换成玩家，我会在意什么？',[
        ('选择','绕过去，能发现什么？','#89e6cc'),
        ('节奏','哪里紧张，哪里能喘口气？','#ffd98c'),
        ('新鲜感','这一跳，和刚才有什么区别？','#a5bbff')],footer='从操作、选择和探索的感受出发')
    diagram('core','我的核心，是反冲平台跳跃',[
        ('一开始','起跳 → 对准 → 反冲 → 落地','#89e6cc'),
        ('练熟以后','路线判断更快，连续操作更稳','#ffd98c'),
        ('我想要的成长','玩家自己，真的变强了','#a5bbff')])
    diagram('repeat','地图换了，熟悉的感觉还在',[
        ('换位置','模块排列可以改变','#89e6cc'),
        ('没换的部分','熟悉的机关、跳法和组合','#ffd98c'),
        ('我的感受','换个顺序，又做了一遍','#ff9d9a')])
    diagram('death','失败之后，我想留下什么？',[
        ('一次死亡','这一局的地图和推进重来','#ff9d9a'),
        ('技术积累','学会的操作，当然还在','#89e6cc'),
        ('长期升级','目前给我的积累感还不够','#ffd98c')])
    diagram('cost','本来以为，随机能省点工作',[
        ('生成器','解决怎么拼、怎么选','#89e6cc'),
        ('玩法模块','每一段，仍然需要设计','#ffd98c'),
        ('持续新鲜','可能还要做得更多','#ff9d9a')])
    diagram('experiment','下一步：先做一个小区域试试',[
        ('精心安排','让反冲跳跃有更明确的节奏','#89e6cc'),
        ('探索与回环','发现新路，带着新能力回来','#ffd98c'),
        ('先验证','有没有更好玩，再决定扩大','#a5bbff')],footer='正在考虑的类银河恶魔城方向 · 小范围实验目标')
    for asset in assets:
        asset['display_label']={
            'web_editor_evidence':'模块库网页 · 固定版本演示',
            'archived_algorithm_comparison':'生成实验存档 · 非实机画面',
            'planned_world_map':'区域规划草案 · 尚未实现',
            'explanatory_diagram':'个人复盘 · 思路示意',
        }[asset['kind']]
    assetspec=dict(schema_version=2,repository='zhipijun1996/map-edit',assets=assets,documents=[])
    # Preserve exact source passages beside the media, separately from subjective narration.
    for repo,commit,root,paths_ in [
        ('map-edit',EDIT,a.map_edit,['README.md']),
        ('map-gen',GEN,a.map_gen,['README.md','experiments/optimization-v1/README.md','experiments/optimization-v2/README.md','experiments/optimization-v2/output/summary.json'])]:
        for i,path in enumerate(paths_):
            b=(root/path).read_bytes()
            assetspec['documents'].append(dict(id=repo+'-'+str(i),repository='zhipijun1996/'+repo,
                commit=commit,path=path,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),
                blob_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
                url=f'https://raw.githubusercontent.com/zhipijun1996/{repo}/{commit}/{path}',
                page_url=f'https://github.com/zhipijun1996/{repo}/blob/{commit}/{path}',verified_quotes=[],
                truth='Exact archived source; scope is document/static experiment, not user experience acceptance'))
    shots=[]
    def shot(title,narration,media,evidence='user',presentation=None,**kwargs):
        if isinstance(media,str):media=[media]
        if isinstance(evidence,str):evidence=[evidence]
        id=f's{len(shots)+1:02}'
        s=dict(id=id,chapter=str((len(shots)//4)+1),title=title,narration=narration,assets=media,
            offsets=[0]*len(media),prs=[],evidence=evidence,transition='cut',
            shot_type='source_image_review' if not presentation else presentation,
            claim_type='personal_retrospective_with_separately_pinned_evidence',
            fact_check='Personal judgments come from the user; map counts and algorithm changes are pinned to the evidence registry. No invented human playtest or full-map physics acceptance.',
            **kwargs)
        if presentation:s['presentation']=presentation
        shots.append(s)
    shot('我可能得换条路','做了一百多个地图模块，折腾了好多轮随机生成。最近，我却开始考虑，要不要把肉鸽这条路先停下来。说不舍得，是真的。但我更怕继续做下去，游戏还是不好玩。','hook',presentation='animated_diagram',emphasis='模块做了一百多个，我却想换方向了')
    shot('先看看都做了什么','这次说说，我到底试了些什么，又为什么越来越不满意。最开始的想法很直接：先把好玩的跳跃做成小模块，再让生成器把它们拼成大地图。','catalog', ['user','catalog'],crop_rect=[515,80,890,920],emphasis='先做模块，再拼大地图')
    shot('不是只有一个素材文件夹','为了能人工审核，我还专门做了这个网页工具。现在库里是一百一十五份模块。可以按地区、接口和难度筛选，再打开具体布局，看看哪一段需要改。',['catalog','catalog-forest'],['catalog'],presentation='montage',crop_rects=[[515,80,890,920],[515,80,890,920]],emphasis='115 份模块 · 当前目录，不等于全部体验合格')
    shot('审核的是具体动作','比如这里，入口在哪，落点够不够，反冲以后怎么接下一步。画出来的路线只是设计预期，还得回到游戏里确认。一个小模块，也不是摆几块地形就结束了。',['module0','module1','module2'],['catalog','user'],presentation='montage',emphasis='网页路线是设计标注，不是物理验收')
    shot('一轮失败，再换一个办法','然后是生成器。换输入，换策略，跑不同的种子。早期接上真实模块库，一批二十个候选，全部被当时的静态目标拒了。再改搜索和回退，有了进展，地图却又容易拉成一条长带。',['early','early'],['v1'],presentation='montage',crop_rects=[[0,0,1500,390],[0,750,1500,510]],emphasis='真实实验记录：先被拒，再改策略')
    shot('同一种子确实在变好','看同一个种子的对比。从基线，到控制外形，再处理垂直衔接和奖励空间。后面这几版，确实比原来规整了。这些改进得承认，不能为了吐槽，把进步也抹掉。',['map-a','map-a'],['v2'],presentation='montage',crop_rects=[[0,0,1100,305],[0,1210,1100,455]],emphasis='同种子对比 · 外形确实改善了')
    shot('合格的范围要讲清楚','后来有一批验证种子，结构、路线目标和外形检查都通过了。但这张图上的通过，回答的是规则有没有满足。整张地图实际操作起来怎么样，还不能凭它下结论。','map-c',['v2'],crop_rect=[0,1020,1100,375],emphasis='静态规则通过 ≠ 整图物理通过 ≠ 好玩')
    shot('把图放大一点','所以我想换回玩家视角看。先别数连了多少个模块。走到这个岔路，我有没有想拐过去的理由？这段连续跳跃，和刚刚那段，玩起来有什么区别？','map-a',['v2','user'],crop_rect=[115,1370,900,280],emphasis='这里的分路，值得我探索吗？')
    shot('把问题换成体验问题','哪里该紧张，哪里能喘口气？绕一段路，有没有新的发现？这些才是我希望关卡能给人的感觉。地图能生成出来以后，我反而更难忽略这些问题。','questions',presentation='animated_diagram',emphasis='作者复盘：问体验，不虚构玩家反馈')
    shot('还要堵住不该有的捷径','我还做了地图封边。没有接出去的接口，要处理掉，免得玩家随便从边上抄过去，把设计好的跳跃绕没了。图里这些红色部分，就是封边的实验示意。','seal',['seal','user'],emphasis='红色：未使用接口的封边 · 实验图',safe_frame=True)
    shot('补规则并不等于补乐趣','但边界也不能乱补。该走的路线、该拿的奖励，不能一起封死。于是又要检查路线、接口和空间。规则越来越完整，我还是没法说，这张随机地图已经好玩了。','module2',['user','catalog','seal'],emphasis='封住非法捷径，也要保护正常路线')
    shot('核心玩法更像跳跳乐','想了一圈，我觉得可能是最初的方向就有点拧巴。我最喜欢的，是连续精准操作，跨过一段难地图的那种快感。失序之钟的核心，也更偏反冲跳跃。','core',presentation='animated_diagram',emphasis='我的核心快感：学会，再跳过去')
    shot('成长更多发生在玩家身上','从起跳、瞄准，到空中接下一次反冲。练熟以后，是我自己判断更快、操作更稳了。我喜欢的那类肉鸽，很多乐趣来自道具组合和战斗构筑。到了我这里，这一块还撑不起来。','module0',['user'],emphasis='操作熟练度在增长，构筑乐趣还不够')
    shot('换位置不等于新体验','再一个，地图每次确实不一样，可库里的模块一直是这些。跳法熟了以后，很容易变成：哦，又是这段，只不过这次放到了左边。排列变了，重复感还在。','repeat',presentation='animated_diagram',emphasis='随机了位置，没随机出同等的新鲜感')
    shot('也不是做出来就都会用上','还有些模块，做出来了，也不一定能被生成器选进去。接口、方向、空间都得合适。我继续加模块，库看着更大了，但真正能组合出来的体验，没有跟着一样快地变丰富。',['catalog','map-b'],['catalog','user'],presentation='montage',crop_rects=[[515,80,890,920],[0,950,1617,355]],emphasis='有模块，和能选上、能组合，是几件事')
    shot('死亡以后留下的感觉','死亡惩罚也让我纠结。技术当然会留下来，可这一局的地图和推进又得重来。长期升级目前给我的感觉，也没强到能抵消这种重复。我想练的是下一段，结果又在重做前一段。','death',presentation='animated_diagram',emphasis='个人感受：不是所有长期进度都被清空')
    shot('想省事，结果工作没少','最扎心的是，我本来以为随机生成能省点关卡设计。结果想让每一局都新鲜，得准备更多模块，还得设计它们怎么组合。省事？想多了。工作没消失，还多了拼装这一层。','cost',presentation='animated_diagram',emphasis='省事？想多了',sfx='pop')
    shot('承认方向可能不合适','做到这里，我现在的感受就是：随机地图，还是没达到我想要的好玩程度。可能肉鸽随机，暂时不适合我这套核心机制。也可能是我还没设计对。我不想再靠多跑几轮，回避这个判断。','map-b',['user','v2'],crop_rect=[0,950,1617,355],emphasis='我的判断，不是对整个类型下结论')
    shot('很不舍，但还得试别的路','一百多个模块，还有这么多轮实验，说推翻就推翻，肯定心疼。感觉之前的活，白干了不少。但投入得越多，我越想确认，我到底是在把游戏做得更好玩，还是只是在舍不得。',['module1','map-c'],['user'],presentation='montage',crop_rects=[None,[0,1020,1100,375]],emphasis='舍不得，不能替我回答好不好玩')
    shot('这张图只是下一步草案','最近，我在考虑类银河恶魔城的方向。这张是打算中的区域地图，还只是规划。不是说接下来立刻把这一整张都做出来。我想先用一个很小的区域，试试另一种关卡组织方式。','plan',['user','plan'],emphasis='区域地图：规划草案 · 尚未实现',safe_frame=True)
    shot('先做一块，看看能不能更好玩','把跳跃的难度、探索路线和回环安排得更具体。学到一个新能力以后，回来发现原来过不去的地方，现在能走了。先看这一小块，能不能比随机拼出来的更有意思。','experiment',presentation='animated_diagram',emphasis='先验证小区域，不承诺整图重做成功')
    shot('还在试，先把方向想明白','模块和审核工具，也许还能继续用。但这次我想先把方向想明白。做了这么久，还是希望最后交出来的，是一个值得玩的游戏。你们觉得，反冲跳跳乐配肉鸽，最缺的会是什么？','plan',['user','plan'],emphasis='还没成功，正在换一种办法试',safe_frame=True)
    spec=copy.deepcopy(json.loads((ROOT/'episodes/ep010-r2.json').read_text()))
    spec.update(episode='ep012',title='做了一百多个模块，我却想放弃随机地图了 | 【失序之钟】独游折腾记 ep11【B站AI创造公开赛】',
        title_candidates=['随机地图没省下工作，我可能得换条路了 | 【失序之钟】独游折腾记 ep11【B站AI创造公开赛】'],
        repository='zhipijun1996/map-edit',asset_spec='episodes/ep012-assets.json',story_ids=['S_RANDOM_MAP_PIVOT'],
        shots=shots,rate='+8%',playback_speed=1.08,target_duration=[180,300],cover_assets=['catalog','plan'],
        music_gain=.075,game_audio_gain=0,
        evidence=[
            dict(id='user',kind='user_testimony',date='2026-11-06',text='User describes extensive generation work, repetitive modules, unsatisfying random layouts, skill-centric platforming, weak perceived progression, and work-saving expectation failing. Tentative Metroidvania experiment; no claim pivot is completed.'),
            dict(id='catalog',kind='pinned_source',repository='zhipijun1996/map-edit',commit=EDIT,path='modules/catalog.json',observed_module_count=115,url=f'https://github.com/zhipijun1996/map-edit/blob/{EDIT}/modules/catalog.json',scope='115 catalog entries, not 115 enjoyable/fully physics-certified modules; current UI snapshot differs from archived 1.1.0 package experiments'),
            dict(id='v1',kind='archived_static_experiments',repository='zhipijun1996/map-gen',commit=GEN,path='experiments/optimization-v1/README.md',url=f'https://github.com/zhipijun1996/map-gen/blob/{GEN}/experiments/optimization-v1/README.md',scope='Real package1.1.0; legacy20 candidates rejected. Expansion/backtracking improve scoped static results, still elongated. Not human fun evaluation.'),
            dict(id='v2',kind='archived_same_seed_comparison',repository='zhipijun1996/map-gen',commit=GEN,path='experiments/optimization-v2/output/summary.json',url=f'https://github.com/zhipijun1996/map-gen/blob/{GEN}/experiments/optimization-v2/output/summary.json',scope='baseline/shape/spatial/stable, same115-module package1.1.0; four variants x40 seeds. Stable20/20 calibration and20/20 validation meet scoped targets. whole-map physics NOT_RUN. Do not infer fun or all-seed reliability.'),
            dict(id='seal',kind='archived_geometry_detail',repository='zhipijun1996/map-gen',commit=GEN,path='experiments/legacy-real-v2/output/gear-seal-detail.png',scope='Red unused-Port seals; seed271028/M02MX. Physics NOT_RUN. Editor Block/occupied outline is not a collision wall.'),
            dict(id='plan',kind='user_uploaded_future_plan',sha256=assets[-1].get('sha256') if assets[-1]['id']=='plan' else hashlib.sha256(target.read_bytes()).hexdigest(),scope='User region concept; no invented completed regions, timings or traversal results.')],
        research_scope=dict(status='episode_targeted_source_scan',repositories={'map-edit':EDIT,'map-gen':GEN},
            coverage='Current catalog and real UI; legacy-real-v1/v2, optimization-v1/v2 READMEs, actual archived comparisons, summary and selected seed layout records. Not a fresh complete multi-branch history census.',
            live_access={'map-edit':'HTTP200; actual browser loaded','map-gen':'HTTP404; source archived comparisons used instead; never described as successful live access'}),
        comparison='Within each four-panel map image: exact same seed, package1.1.0, scale. Different seed images are examples, not before/after. Current module UI is pinned newer source, not the exact archived runtime.',
        comparison_review='核对个人感受、静态实验结果与规划边界；评价提问不是玩家测试；地图四联图同种子，跨图不同种子；规划图尚未实现。',
        rights=[dict(kind='project_interfaces_and_experiment_images',status='User owns repositories and requested their use; no blanket third-party rights claim'),
            dict(kind='region_plan',status='User-supplied planning image, not gameplay'),
            dict(kind='editorial_diagrams',status='Original project-authored explanatory graphics, MIT'),
            dict(kind='music',status=spec['music_asset']['license_status']),
            dict(kind='font',status='Noto CJK SIL OFL1.1'),dict(kind='voice',status='Edge synthetic Mandarin; no voice cloning')],
        bilibili_body='做了一百多个模块，还做了网页审核工具，随机地图也跑了很多轮实验。结构确实有进步，但从自己的体验看，离“好玩”还是有距离。\n\n这次聊聊我为什么开始怀疑肉鸽随机是否适合反冲平台跳跃，以及最近在考虑的类银河恶魔城小区域实验。区域图是规划草案，目前还没实现。地图实验图展示静态结构，不冒称整图物理与玩家体验验收通过。\n\n地图生成器：https://zhipijun1996.github.io/map-gen/ （制作时首页404，片中采用固定源码的真实实验存档）\n模块库：https://zhipijun1996.github.io/map-edit/\n\n#B站AI创造公开赛#\n分区建议：单机游戏。标签：独立游戏、游戏开发、Godot、AI开发、肉鸽、关卡设计、失序之钟、B站AI创造公开赛。')
    spec['cover_assets']=['catalog','map-a']
    spec['cover']=dict(series='失序之钟 · 独游折腾记 ep11',left_label='真实模块库',right_label='生成实验存档',
        line1='115 个模块以后',line2='我想放弃随机地图了')
    # Keep factual scope in the source manifest. Audience labels explain the
    # actual image without turning the film into an internal compliance log.
    labels={
        's03':'115 份模块，还要一份份审',
        's04':'先看布局，再回游戏确认',
        's07':'规则过关了，体验呢？',
        's09':'地图能拼出来，还得值得玩',
        's16':'技术留下了，重复的路还得走',
        's18':'这套随机，还撑不起我想要的乐趣',
        's21':'先做小块，把好不好玩试出来'}
    for s in shots:
        if s['id'] in labels:s['emphasis']=labels[s['id']]
    # This inherited optional field belongs to the previous episode only.
    for k in ['mindmap','mindmap_outline','original_music']:
        spec.pop(k,None)
    write(ROOT/'episodes/ep012-assets.json',assetspec)
    write(ROOT/'episodes/ep012.json',spec)
    stories=json.loads((ROOT/'research/stories.json').read_text())
    stories=[s for s in stories if s['id']!='S_RANDOM_MAP_PIVOT']
    stories.append(dict(id='S_RANDOM_MAP_PIVOT',event='115个模块与多轮生成之后，开始怀疑肉鸽方向',date='2026-11-06',
        background='反冲平台跳跃，最初希望模块化随机生成减少关卡设计负担',conflict='静态实验逐渐进步，作者仍感觉重复、新鲜感弱、长期积累不足，设计工作未减少',
        attempts=['115份模块与真实网页审核','真实库接入、搜索与回退','外形、垂直空间与奖励空间优化','未使用接口封边'],
        result='Tentative small Metroidvania experiment, not an implemented successful pivot',
        commit=GEN,base_commit=None,pr=None,branch='map-gen/main',
        sources=[e for e in spec['evidence'] if e['id'] in ['catalog','v1','v2','seal']],
        media=['catalog','module0','map-a','map-b','map-c','seal','plan'],
        recordability=dict(source_available=True,saved_media_available=True,historical_rebuild='Exact module-editor snapshot captured; original algorithm map images available; whole-map physics not run for this episode'),
        evidence_status='Pinned catalog count, archived experimental outputs and actual web capture; subjective dissatisfaction and tentative pivot from user testimony',
        truth_status='source-backed effort + user subjective retrospective + future plan',
        video_potential=dict(reason='clear sunk-effort conflict; honest unresolved tradeoff',priority='high')))
    write(ROOT/'research/stories.json',stories)
    print('Authored',len(shots),'shots;',len(assets),'assets; narration chars',sum(len(s['narration']) for s in shots))


if __name__=='__main__':main()
