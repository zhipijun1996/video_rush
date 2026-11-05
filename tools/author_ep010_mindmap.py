"""Reframe ep010 as a personal retrospective with one stable hierarchy.

No renderer fork: all diagrams use the existing animated vector primitives.
Node IDs/parentage stay constant across overview and four-level detail views.
"""
from pathlib import Path
import copy
import json

ROOT = Path(__file__).resolve().parents[1]
PAPER, INK, MUTED = '#f3f0e7', '#293440', '#707b83'
COLORS = ['#197d78', '#526caa', '#a56a26', '#a05269']
BRANCHES = [
    ('目标与设计', ['需求文档', '架构文档', '模块设计']),
    ('让AI接手', ['AGENTS入口', 'Skills流程', '按需上下文']),
    ('每次迭代', ['小步闭环', '实际验证', '任务与交接']),
    ('持续维护', ['规则归属', '最终稿维护', '历史与迁移'])]
OVERVIEW = [
    ['需求｜目标、范围、完成依据', '架构｜框架、目录、模块边界', '设计｜具体行为与状态衔接'],
    ['AGENTS｜从哪里开始', 'Skills｜重复流程怎样做', '上下文｜本次需要读什么'],
    ['小步闭环｜真实入口接起来', '实际验证｜结果与体验分开', '任务交接｜进度、阻塞、下一步'],
    ['规则归属｜一处定义，其余引用', '最终稿维护｜直接重整正文', '历史迁移｜保留追溯，退出旧入口']]


def text(x, y, value, size=36, color=INK, width=1700, group=None, bold=False):
    e=dict(type='text',x=x,y=y,text=value,size=size,color=color,width=width,bold=bold)
    if group:e['group']=group
    return e


def box(x,y,w,h,color=INK,group=None,fill=PAPER,radius=18):
    e=dict(type='rect',bounds=[x,y,w,h],fill=fill,color=color,stroke_width=2,radius=radius)
    if group:e['group']=group
    return e


def edge(points,color,group=None,width=4):
    e=dict(type='line',points=points,color=color,width=width,arrow=False)
    if group:e['group']=group
    return e


def track(name,start=.04,end=1,offset=(35,0),travel=.14,to=(0,0)):
    return dict(id=name,start=start,end=end,**{'from':list(offset),'to':list(to)},travel=travel,fade=.035)


def header(title,subtitle,active=None):
    g=dict(layout='diagram',background=PAPER,elements=[
        text(92,119,'失序之钟 · 我的项目管理复盘',29,MUTED,width=600),
        text(92,178,title,61,INK,bold=True),text(94,262,subtitle,32,MUTED)],motion_groups=[])
    for i,(name,_) in enumerate(BRANCHES):
        x=790+i*258
        g['elements'].append(text(x,121,name,29,COLORS[i] if active in (None,i) else '#a4a6a3',235,bold=active==i))
        if active==i:g['elements'].append(edge([[x,160],[x+215,160]],COLORS[i],width=5))
    return g


def root(g,group=None):
    g['elements'] += [box(84,527,270,123,INK,group,fill=INK),
        text(111,548,'AI项目管理',39,'#fffaf0',230,group,True),
        text(112,605,'我的踩坑总结',28,'#e1e4df',230,group)]


def overview(title,subtitle,highlight=None,*,complete=False):
    g=header(title,subtitle,highlight)
    root(g)
    for i,((name,_),labels) in enumerate(zip(BRANCHES,OVERVIEW)):
        color=COLORS[i] if highlight in (None,i) else '#a5aaa9'
        y=365+i*140;name_id=f'branch{i}'
        g['elements'] += [edge([[354,589],[409,589],[409,y+27],[477,y+27]],color,name_id),
            box(477,y-8,370,74,color,name_id),text(499,y+9,name,39,color,330,name_id,True)]
        for j,label in enumerate(labels):
            yy=y-40+j*44
            g['elements'] += [edge([[847,y+27],[918,y+27],[918,yy+19],[978,yy+19]],color,name_id,width=3),
                text(993,yy,label,32,color,810,name_id,bold=j==0)]
        g['motion_groups'].append(track(name_id,.025+i*.145,offset=(25,0),travel=.13))
    if complete:
        # Return to the already-expanded map. Attention moves across branches;
        # the whole hierarchy does not restart its entrance animation.
        for e in g['elements']:e.pop('group',None)
        g['motion_groups']=[]
        for i,(name,_) in enumerate(BRANCHES):
            yy=365+i*140;ident=f'focus{i}';co=COLORS[i]
            g['elements'] += [box(477,yy-8,370,74,co,ident,fill='#e0e7dc'),
                text(499,yy+9,name,39,co,330,ident,True)]
            g['motion_groups'].append(track(ident,.025+i*.18,end=.025+i*.18+.17,offset=(0,0),travel=.07))
    # A late connecting stroke keeps the hierarchy's growth visible; no fake
    # runtime/algorithm measurement is inferred from this editorial animation.
    g['elements'] += [edge([[109,874],[1810,874]],'#bcb7a6','summary',width=3),
        text(112,880,'当前规范 + 个人总结 · 还在边做边改' if complete else '从问题出发，把经验分层整理',28,MUTED,1650,'summary')]
    g['motion_groups'].append(track('summary',.73,offset=(-45,0),travel=.18))
    g['hierarchy_view']=dict(mode='overview',root='root',active_branch=highlight,node_ids=['root']+[f'b{i}' for i in range(4)]+[f'b{i}-t{j}' for i in range(4) for j in range(3)])
    return g


def detail(branch,topic,title,reflection,leaves):
    g=header(title,reflection,branch);root(g);c=COLORS[branch]
    g['elements'] += [text(92,319,'我在解决的问题',28,MUTED,290),text(431,319,'四件事中的这一件',28,MUTED,330),
        text(839,319,'具体怎么做',28,MUTED,340),text(1295,319,'我的理解 / 游戏里的例子',28,MUTED,535),
        edge([[354,589],[424,589]],c),box(424,539,330,102,c),
        text(444,570,BRANCHES[branch][0],40,c,290,bold=True)]
    for j,label in enumerate(BRANCHES[branch][1]):
        yy=397+j*171;co=c if j==topic else '#a0a7a8'
        g['elements'] += [edge([[754,590],[793,590],[793,yy+38],[829,yy+38]],co,width=4 if j==topic else 2),
            box(829,yy,342,77,co,fill='#fffaf0' if j==topic else PAPER),
            text(850,yy+22,label,36,co,300,bold=j==topic)]
    active_y=397+topic*171+38
    for j,(heading,body) in enumerate(leaves):
        yy=365+j*174;name=f'leaf{j}'
        g['elements'] += [edge([[1171,active_y],[1226,active_y],[1226,yy+45],[1283,yy+45]],c,name,width=3),
            text(1298,yy+7,heading,37,c,510,name,True),text(1298,yy+63,body,31,INK,510,name),
            edge([[1297,yy+112],[1797,yy+112]],'#d7d0bc',name,width=2)]
        g['motion_groups'].append(track(name,.06+j*.23,offset=(28,0),travel=.19))
    g['elements'] += [text(94,866,'同一张图：'+BRANCHES[branch][0]+' → '+BRANCHES[branch][1][topic],29,MUTED,1680,'path')]
    g['motion_groups'].append(track('path',.72,offset=(0,18),travel=.17))
    g['hierarchy_view']=dict(mode='detail',root='root',active_branch=branch,active_topic=topic,
        node_ids=['root',f'b{branch}']+[f'b{branch}-t{j}' for j in range(3)]+[f'b{branch}-t{topic}-e{j}' for j in range(3)],
        parent_edges=[['root',f'b{branch}']]+[[f'b{branch}',f'b{branch}-t{j}'] for j in range(3)]+[[f'b{branch}-t{topic}',f'b{branch}-t{topic}-e{j}'] for j in range(3)])
    return g


def write(path,data):
    p=ROOT/path;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    s=copy.deepcopy(json.loads((ROOT/'episodes/ep010.json').read_text()))
    old_assets=json.loads((ROOT/'episodes/ep010-assets.json').read_text())
    rows=[]
    def ov(title,voice,refs,highlight=None,complete=False):
        rows.append((title,voice,refs,overview(title,'一次停工重构之后，我补上的管理思路',highlight,complete=complete)))
    def dt(b,t,title,voice,refs,examples,reflection):
        rows.append((title,voice,refs,detail(b,t,title,reflection,examples)))
    ov('停工整理之后，我把经验归成一张图',
       '上一期我吐槽，AI把代码仓写得越来越乱。停工整理之后，这次想分享一下，我现在怎么理解项目管理。我把这些想法整理成了一张图。',
       ['user-method','user-summary-r2'])
    ov('我现在主要在管这四件事',
       '代码能跑起来，还不够。目标、规则和进度散在各处，换个会话就得重新解释。所以我现在主要管四件事：目标设计，任务接手，持续迭代，还有规则维护。',
       ['user-method','doc-agents','user-summary-r2'])
    dt(0,0,'需求里，我最想讲清的是“为什么做”',
       '第一层，是先把想做的东西说清楚。拿反冲跳跃来说，我想要的是用射击改变位移，产生新的路线选择。需求文档里，我会先讲这种体验，再讲这次的范围和完成依据。',
       ['user-method','doc-game-design'],
       [('玩家体验','射击位移，产生路线选择'),('本次范围','例如只调整反冲衔接'),('完成依据','连续操作与中断后的恢复')],
       '先讲目标，再讨论怎么实现')
    dt(0,1,'架构让我知道，一件事到底归谁管',
       '然后是架构文档。我觉得光有目录还不够，软件框架、模块边界和状态归属也得讲清楚。失序之钟继续用Godot，人物、战斗和应用各有职责。',
       ['doc-architecture','doc-module-map','user-method'],
       [('软件框架','Godot：节点、场景与资源'),('目录归属','人物、战斗、应用分工'),('状态与接口','谁修改状态，谁只做表现')],
       '目录结构是职责边界的落点')
    dt(0,1,'比如反冲，运动规则只该有一个入口',
       '比如输入提交意图，人物运动组件执行移动，动画音效跟着事件走。这个边界写清楚，才方便发现：新代码写了，正式入口却还在用旧逻辑。',
       ['doc-architecture','doc-player'],
       [('输入意图','Router转交操作请求'),('实际运动','PlayerMotor负责执行'),('表现反馈','消费已经接受的事件')],
       '据当前架构规范简化，不是执行录像')
    dt(0,2,'设计文档，是把体验落到具体行为',
       '模块设计再往下一层：什么条件触发，过程怎么衔接，落地、受伤和暂停时怎么退出。这样，一句“把手感做好”，才变成能讨论、能检查的事情。',
       ['doc-player','doc-agents'],
       [('触发前提','输入、资源、当前动作状态'),('过程衔接','射击、位移怎样配合'),('退出与中断','落地、受伤、暂停后的恢复')],
       '从目标到行为，再到实际检查')
    dt(0,2,'这三层，我会跟着功能一起补',
       '这三份文档，也不用一次写完所有未来细节。我现在更认同，先把当前要做的说清楚，再跟着功能迭代。否则设计写得很完整，真实入口依然可能没接上。',
       ['user-method','doc-development','external-spec-kit'],
       [('最小清晰版本','先明确当前要做的事'),('随功能更新','只补受影响的设计'),('接回真实入口','规则、实现与场景一起交付')],
       '需求 → 架构 → 模块设计，层层对应')
    dt(1,0,'第二层，是让下一个AI会话接得上',
       '第二层，是让AI知道从哪儿接手。我的做法是把AGENTS当短入口：先看基线和当前状态，再找任务、交接，以及相关设计和代码。细节留在它们各自的位置。',
       ['doc-agents','external-agents-standard'],
       [('当前基线','分支、版本与实际实现'),('任务和交接','这次目标、阻塞、下一步'),('实际入口','规范、代码和验证导航')],
       '入口负责导航，不承担整仓知识')
    dt(1,2,'我更在意这次读什么，而不是全读完',
       '改人物动作，就先读人物物理、输入约束和相关实现。其他资料，沿直接依赖继续找。我想留下的是这次真正有用的上下文，不是把全部历史再讲一遍。',
       ['doc-agents','doc-doc-index','doc-player-skill'],
       [('人物任务先读','物理、输入与相关实现'),('沿直接依赖继续','有影响再查资源和表现'),('历史按需追溯','不混作每天开工的规则')],
       '先把有限的上下文用在当前问题上')
    dt(1,1,'Skills，是把反复提醒的事固定下来',
       '那些反复要提醒的步骤，我会放进Skills。什么情况用，先看什么，怎么做，最后拿什么结果交付。对我来说，它是在把工作经验变成可复用的流程。',
       ['user-method','doc-player-skill','doc-integration-skill'],
       [('适用条件与材料','这类任务先读什么'),('固定操作顺序','规范、实现、真实接入'),('验证与交付','实际结果和仍然缺的部分')],
       '入口帮忙找到资料，Skills组织执行顺序')
    dt(1,1,'流程最后，我还是得看实际结果',
       '比如人物优化，先统一脚底、枪口和身体关系，再看连续动作、左右朝向和中断恢复。当然，写进Skill不等于AI就做对了，最后还得回到实际结果。',
       ['doc-player-skill'],
       [('先统一身体关系','脚底、枪口、附件与比例'),('再看连续动作','朝向、瞄准和反冲衔接'),('检查异常中断','暂停、死亡及正式镜头')],
       '摘意自当前player-creator；未宣称本轮新增成果')
    dt(2,0,'第三层，我更愿意一轮只打通一件事',
       '第三层，是每次迭代怎么收住。现在我会把任务切小，比如这一轮只调整反冲衔接，把设计、实现和真实消费者一起打通，再扩下一件事。',
       ['user-method','doc-development','external-small-cls'],
       [('一个明确目标','例如调整反冲动作衔接'),('一段完整闭环','规范、实现与真实消费者'),('差异可以看懂','便于检查，也方便回退')],
       '范围收小，交付一个能确认的结果')
    dt(2,1,'“通过了”，我会多看一句通过了什么',
       '验证这块，我觉得最容易混淆的是“通过了什么”。当前日常CI只有四项基础检查，功能改动再选专项。代码通过、操作手感和手机表现，是不同的结论。',
       ['doc-agents','doc-current','doc-development'],
       [('日常基础CI','project、import、smoke、contracts'),('按影响选专项','移动、资源、恢复等相关回归'),('体验单独判断','技术通过不代签手感与设备')],
       '每个通过结论，都要有具体覆盖范围')
    dt(2,2,'交接里，我最需要的是下一步能继续',
       '项目管理上，任务表维护进度，交接记录基线、改动、检查、阻塞和下一步。换个会话后，我最需要的是知道怎么接着干，而不是看一句“已完成”。',
       ['doc-management','doc-agents'],
       [('任务表','进度只维护一处'),('当前交接','基线、写集、检查与阻塞'),('下一条动作','新会话能继续执行')],
       '一行任务 + 一份当前交接')
    dt(2,2,'管理材料，也要能帮我少做点重复工作',
       '这次整理里，我也在给管理做减法。普通修复，一行任务和一份交接就够；新地区、新怪物，再按需要看美术和玩法。我不想最后又变成填表比赛。',
       ['pr135','doc-management','doc-development','user-method'],
       [('普通修复','任务、交接和相关检查'),('新地区或新怪物','按需观察美术与玩法'),('材料有没有用','能帮助继续工作才值得保留')],
       'PR135已合入轻量流程；管理不是表格越多越好')
    dt(3,0,'第四层，是持续维护唯一的现行规则',
       '最后一层，是文档怎么持续维护。我现在很看重一条：同一件事只在一个地方定义。设计管行为，配置管数值，其他文档引用它，尽量减少多个答案。',
       ['doc-agents','doc-doc-index','doc-management'],
       [('行为与规则','放在所属设计正文'),('具体数值','引用实际运行配置'),('其他文档','链接引用，减少重复定义')],
       '各自有归属，才不容易越写越冲突')
    dt(3,1,'这句话，我真希望最开始就写进去',
       '还有这句，我真希望最开始就写进去：所有文档修改，按照最终交付件的形式更改，不进行补丁式修改和强调。',
       ['user-method','doc-agents'],
       [('修改受影响正文','整理成当前完整版本'),('移除被替代内容','不是末尾再强调一句'),('通读全文','引用和实现一起核对')],
       '文档始终按当前最终稿维护')
    dt(3,1,'正文讲现在，修订记录讲为什么变了',
       '我的理解是，规则变了，就把正文整理成当前完整版本。历史交给Git和PR；有必要的话，额外维护简要修订记录。读规范时，就不用自己猜到底哪句话还有效。',
       ['user-method','doc-agents','doc-management'],
       [('现行正文','解释现在怎么做'),('历史与原件','通过Git、PR保留追溯'),('简要修订记录','单独说改了什么、为什么')],
       '最终稿会继续迭代，但不叠加互相覆盖的补丁')
    dt(3,2,'旧方案退出，也要照顾还在用它的地方',
       '旧方案也不能直接一删了之。先查还有谁在用，接通新实现，验证后再清理重复。要让旧规则退出当前入口，同时留得下追溯和恢复的依据。',
       ['doc-architecture','doc-integration-skill','doc-doc-index'],
       [('先核真实消费者','引用、动态加载、导出和版本'),('接通新的实现','验证实际调用和恢复边界'),('再清重复与旧入口','历史保留，现行采用明确')],
       '文件在旧目录，不等于已经没人用了')
    ov('串起来看，就是我现在这张管理图',
       '串起来看，需求决定目标，架构明确边界，设计落实行为；入口和Skills帮AI接手，每轮靠实现、验证和交接往前走。发现变化，再回到对应的正文。',
       ['user-method','doc-agents','doc-management'],complete=True)
    ov('规范已经整理，项目还有很多没做完',
       '失序之钟的这轮文档和流程整理已经合入，但地图整合、对象设计和体验还没做完。这张图也是我目前的总结，能不能长期减少返工，还得继续用。',
       ['pr134','pr135','doc-current','doc-data'],complete=True)
    ov('这次补课，我先总结到这里',
       '游戏还没做完，我先补了一门项目管理。希望这些踩坑后的想法能有点参考价值。你们在AI大项目里，哪些管理办法真的有用？也欢迎给我支招。',
       ['user-method','user-summary-r2','doc-current'],complete=True)
    assets=[];shots=[]
    for i,(title,voice,refs,g) in enumerate(rows,1):
        ident=f't{i:02}'
        if i==1:
            g['elements']=[e for e in g['elements'] if not
                (e['type']=='text' and e['x']>=978) and not
                (e['type']=='line' and e['points'][0][0]==847)]
            g['hierarchy_view']['node_ids']=['root']+[f'b{j}' for j in range(4)]
        assets.append(dict(id=ident,origin='editorial',kind='animated_explanatory_diagram',graphic=g,
            display_label='个人经验复盘 · 层次化思维导图',
            license='Original Video Rush mindmap and lettering, MIT; user-authorized repository facts.',
            truth='Original editorial hierarchy with progressive branch/leaf reveal. Not gameplay, a repository screenshot, AI execution, empirical improvement or human acceptance evidence.'))
        shots.append(dict(id=ident,chapter=f'{i:02}',title=title,narration=voice,assets=[ident],offsets=[0],
            presentation='animated_diagram',shot_type='hierarchical_mindmap_retrospective',transition='cut',
            sfx='pop' if i in (1,8,12,16) else None,emphasis='停工整理后，我补上的管理经验' if i==1 else '',prs=[],evidence=refs,
            fact_check='Same personally inspected frozen repository documents as ep010. First-person interpretation reflects user framework and current recommendations. No fabricated past incidents or measured long-term success.',
            claim_type='personal_retrospective_with_pinned_repository_example',same_seed_comparison=False,
            mindmap_view=g['hierarchy_view']))
    fullmap=overview('我的AI项目管理复盘','先想清楚 → 让AI接手 → 小步交付 → 持续维护',complete=True)
    assets.append(dict(id='mindmap',origin='editorial',kind='original_explanatory_diagram',graphic=fullmap,
        display_label='完整分层思维导图 · 个人总结',license='Original Video Rush, MIT',truth='One stable authored hierarchy, not a proof of completed method or game.'))
    s.update(episode='ep010-r2',title='AI把代码仓写乱之后，我补上的项目管理经验 | 【失序之钟】独游折腾记 ep09【B站AI创造公开赛】',
        title_candidates=['停工重构之后，我整理了这张AI项目管理图 | 【失序之钟】独游折腾记 ep09【B站AI创造公开赛】'],
        asset_spec='episodes/ep010-r2-assets.json',shots=shots,cover_assets=['t01','mindmap'],
        editorial_status='source_checked_human_phone_review_pending',rate='+8%',playback_speed=1.02)
    s['evidence'].append(dict(id='user-summary-r2',kind='user_direction',date='2026-11-05',
        text='User wants a reflective experience-sharing tone and a hierarchical mindmap; retain the complete personal framework and unfinished status, revise the full film rather than only adding a final static diagram.'))
    s['research_scope']['revision']='ep010-r2: same main rechecked unchanged48cddb on2026-11-05. User requests editorial/visual revision; no new runtime tests or full-history research claimed.'
    s['mindmap']=dict(root='AI项目管理：我的踩坑总结',branches=[dict(id=f'b{i}',title=name,topics=[dict(id=f'b{i}-t{j}',title=t) for j,t in enumerate(topics)]) for i,(name,topics) in enumerate(BRANCHES)],
        levels=['个人复盘主题','四条管理主线','具体方法','游戏例子与检查依据'],
        overview_asset='mindmap',editable_delivery='source-evidence/mindmap.svg',
        animation='Same node IDs/parentage/colors. Overview → one branch and topic with three subordinate leaves → recap. No camera zoom or real runtime execution claimed.')
    c=header('踩坑之后，我怎么管AI项目','失序之钟 · 独游折腾记 ep09 · 我的经验复盘')
    c['elements']=[text(100,100,'失序之钟 · 独游折腾记 ep09',42,COLORS[0]),
        text(100,204,'踩坑之后',117,INK,bold=True),text(100,365,'我怎么管AI项目',112,COLORS[0],bold=True),
        text(104,532,'把自己的管理经验，整理成一张图',44,MUTED)]
    c['motion_groups']=[]
    c['elements'] += [box(100,704,310,117,INK,fill=INK),text(121,742,'我的管理复盘',40,'#fffaf0',270,bold=True)]
    for i,(name,_) in enumerate(BRANCHES):
        x=607+(i%2)*650;y=668+(i//2)*139;co=COLORS[i]
        c['elements'] += [edge([[410,762],[522,762],[522,y+48],[x,y+48]],co,width=4),
            box(x,y,532,98,co),text(x+26,y+29,name,43,co,480,bold=True)]
    c['elements'].append(text(104,976,'项目和这套方法都还在打磨 · 原创思维导图',29,MUTED))
    s['cover']=c
    s['bilibili_body']='''上一期停工整理代码仓之后，这次想分享一点我对AI项目管理的理解。我把踩坑后的想法归成一张分层思维导图：

1. 目标与设计：需求、架构、模块设计。
2. 让AI接手：AGENTS入口、Skills流程、按任务读取上下文。
3. 每次迭代：小步闭环、实际验证、任务与交接。
4. 持续维护：一处定义规则、按最终交付件重整正文、保留历史并迁出旧入口。

讲到哪里就展开对应分支，最后回看完整层次。结合《失序之钟》当前规范和反冲动作举例，是个人复盘与建议，项目还没做好，方法也还在边用边改。

最想早点写进去的一句：所有文档修改，按照最终交付件的形式更改，不进行补丁式修改和强调。需要时可以另外维护简要修订记录。

AI配音、原创动态思维导图和轻BGM；未使用合成实机、虚构AI对话或假用户反馈。规范冻结在main48cddb6a，PR134/135已合入；长期管理效果和游戏体验仍未完成验证。完整思维导图SVG附在下载包source-evidence/mindmap.svg。

口播、层级结构与来源：
https://github.com/zhipijun1996/video_rush/blob/main/docs/ep010-r2.md
游戏：https://github.com/zhipijun1996/gunman-rush
补充阅读：https://github.com/github/spec-kit
https://github.com/agentsmd/agents.md
https://google.github.io/eng-practices/review/developer/small-cls.html

#B站AI创造公开赛# #独立游戏# #AI# #项目管理# #Codex#

分区建议：游戏 / 单机游戏。用户审片通过后再上传，投稿时需关联官方活动话题。'''
    s['comparison_review']='是否像开发者分享自己的复盘；思维导图的父子层次、当前焦点和例子是否一眼能对应；未声称方法已成熟或项目完成。'
    write('episodes/ep010-r2.json',s)
    write('episodes/ep010-r2-assets.json',dict(schema_version=2,repository=s['repository'],documents=old_assets['documents'],assets=assets))
    md='# '+s['title']+'\n\n个人经验复盘口播 · 尚待用户审片 · 与原ep010独立保存。\n\n'
    md+=''.join('## '+x['id']+' · '+x['title']+'\n\n'+x['narration']+'\n\n' for x in shots)
    (ROOT/'docs/ep010-r2-script.md').write_text(md)
    mm='# 我的AI项目管理复盘\n\n与整片一致的四层结构；末层为个人概括和例子，不是新增游戏实现。\n\n```mermaid\nmindmap\n  root((我的AI项目管理复盘))\n'
    for i,(name,topics) in enumerate(BRANCHES):
        mm+='    '+name+'\n'
        for j,t in enumerate(topics):mm+='      '+t+'\n        '+OVERVIEW[i][j].split('｜',1)[1]+'\n'
    mm+='```\n\n原始全图随成片附在source-evidence/mindmap.svg；视频中按同一父子结构逐层展开。\n'
    (ROOT/'docs/ep010-r2-mindmap.md').write_text(mm)
    print('Authored',len(shots),'retrospective shots;',sum(len(x['narration']) for x in shots),'characters; one hierarchy, four branches and12 topics')


if __name__=='__main__':main()
