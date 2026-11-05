"""Author ep010's evidence-linked script and original animated diagrams.

This prepares deterministic creative assets; it does not change the game or
replace the existing ten-stage production pipeline.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'build/research/ep010'
COMMIT = '48cddb6a70983b0a0206304d18c98d274a9a7549'
BG, PANEL, WHITE, DIM = '#101b2a', '#1d3044', '#f1f5fb', '#a8bacd'
GREEN, GOLD, BLUE, RED = '#85dfc2', '#ffd17b', '#8ebcff', '#ff8d99'


def dump(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def text(x, y, value, size=40, color=WHITE, width=1700, group=None, bold=False):
    e = dict(type='text', x=x, y=y, text=value, size=size, color=color, width=width, bold=bold)
    if group:
        e['group'] = group
    return e


def rect(x, y, w, h, color=GREEN, group=None, fill=PANEL):
    e = dict(type='rect', bounds=[x, y, w, h], color=color, fill=fill, radius=20, stroke_width=3)
    if group:
        e['group'] = group
    return e


def line(points, color=GREEN, group=None, arrow=True):
    e = dict(type='line', points=points, color=color, width=6, arrow=arrow)
    if group:
        e['group'] = group
    return e


def motion(name, start=0.02, end=1, a=(0, 60), b=(0, 0), travel=.15):
    return dict(id=name, start=start, end=end, **{'from': list(a), 'to': list(b)}, travel=travel, fade=.025)


def base(section, title, subtitle=''):
    return dict(layout='diagram', background=BG,
                elements=[text(92, 121, section, 30, GREEN),
                          text(92, 177, title, 67, GOLD, bold=True),
                          text(96, 275, subtitle, 33, DIM)], motion_groups=[])


def card(g, name, x, y, w, title, body, color=GREEN, start=.02, end=1, a=(0, 65), b=(0, 0), h=190):
    g['elements'] += [rect(x, y, w, h, color, name), text(x+25, y+25, title, 43, color, w-50, name, True)]
    for i, value in enumerate(body.split('\n')):
        g['elements'].append(text(x+25, y+91+i*44, value, 33, WHITE, w-50, name))
    g['motion_groups'].append(motion(name, start, end, a, b))


def takeaway(g, value, start=.68, color=GOLD):
    g['elements'] += [rect(96, 748, 1725, 110, color, 'take'), text(125, 775, value, 41, color, 1660, 'take', True)]
    g['motion_groups'].append(motion('take', start, a=(0, 35), travel=.12))


def triplet(section, title, subtitle, cards, conclusion):
    g = base(section, title, subtitle)
    for i, (heading, body, color) in enumerate(cards):
        card(g, f'c{i}', 96+584*i, 392, 552, heading, body, color, .025+i*.17, a=((60 if i%2 else -60), 35))
        if i:
            name=f'link{i}'
            g['elements'].append(line([[96+584*i-27, 482], [96+584*i-5, 482]], DIM, name))
            g['motion_groups'].append(motion(name, .1+i*.17, a=(0, 0)))
    takeaway(g, conclusion)
    return g


def two(section, title, subtitle, left, right, conclusion):
    g = base(section, title, subtitle)
    card(g, 'left', 96, 370, 810, left[0], left[1], left[2], .03, a=(-65, 0), h=265)
    card(g, 'right', 1011, 370, 810, right[0], right[1], right[2], .31, a=(65, 0), h=265)
    takeaway(g, conclusion)
    return g


def diagrams():
    result=[]
    result.append(two('先把项目管起来', 'AI写得越快，项目越难接手？', '上一期停工重构之后，我开始补开发规矩',
        ('继续加功能', '旧规则、新规则都在\n改完这边，又碰坏那边', RED),
        ('先明确当前规则', '做什么、归谁管、怎么验\n每次任务都能接得上', GREEN), '这期讲我的做法，还在调整，尚未验证成熟。'))
    result.append(triplet('为什么需要这套机制', '先回答三个问题', '让新会话找到当前规则，而不是重读全部历史',
        [('目标', '这次到底要解决什么？', GREEN), ('边界', '哪些地方能改、谁负责？', BLUE), ('证据', '什么结果才算做完？', GOLD)], '我的目标：减少猜测、重复规则和无边界改动。'))
    result.append(triplet('01 · 需求先行', '先写玩家要得到什么', '示例：反冲跳跃 · 根据现有设计整理',
        [('目标体验', '射击辅助位移\n让平台路线多一种解法', GREEN), ('明确边界', '本次只调整反冲衔接\n不顺手重做整个成长系统', BLUE), ('观察结果', '射击后能接回移动\n落地与受伤状态正确', GOLD)], '需求先说体验和验收，再讨论用哪些类。'))
    result.append(two('01 · 需求先行', '“更爽一点”，不够指导开发', '检查正常操作与中断；手感仍需要实际体验',
        ('模糊要求', '把跳跃手感优化一下\n做完告诉我就行', RED),
        ('可检查的要求', '能否衔接？中断后是否恢复？\n录一段连续操作，再判断体验', GREEN), '先把“做完”讲清楚，减少最后才发现理解不同。'))
    result.append(triplet('02 · 架构', '目录结构只是第一层', '当前仓库：Godot Node / Scene / Resource，按功能组织',
        [('框架与入口', 'Godot\ngame/application/', GREEN), ('模块目录', 'game/player/\ngame/combat/', BLUE), ('接口与职责', '谁发请求，谁修改状态\n谁只负责表现', GOLD)], '架构写边界、依赖和调用，文件夹用来落实它。'))
    g=base('02 · 架构落到真实例子', '反冲动作，谁说了算？', '据当前架构及人物物理规范简化 · 不是引擎执行录像')
    for i,(name,body,color) in enumerate([('输入 / Router','提交操作意图',BLUE),('能力 / PlayerMotor','执行运动与碰撞',GREEN),('动画 / 音效','响应已接受的事件',GOLD)]):
        card(g,f'node{i}',96+584*i,385,552,name,body,color,.02+i*.17)
    for i in range(2):
        name=f'event{i}';g['elements'].append(line([[390+584*i,653],[925+584*i,653]],GREEN,name));g['motion_groups'].append(motion(name,.39+i*.16,a=(-200,0),b=(0,0),travel=.22))
    takeaway(g,'表现不能另算一套移动、伤害或资源规则。',.76)
    g['elements'] += [rect(682,635,210,45,GREEN,'accepted'),text(698,641,'接受事件',28,GREEN,180,'accepted')]
    g['motion_groups'].append(motion('accepted',.5,.96,a=(-360,0),b=(230,0),travel=.36))
    result.append(g)
    result.append(two('02 · 架构约束', '先找已有入口，再加新代码', '当前架构明确要求：不要新增无人调用的helper',
        ('容易出现的偏差', '新建一个“统一管理器”\n原入口继续运行旧逻辑', RED),
        ('我的约束', '定位实际消费者\n迁到同一实现，再清重复', GREEN), '“新文件写好了”不等于“正式入口用上了”。'))
    result.append(triplet('03 · 模块设计', '把体验拆成能开发的行为', '需求讲为什么；架构讲归谁；设计讲具体怎么发生',
        [('进入', '什么输入触发\n需要哪些资源与前提', GREEN), ('过程', '方向如何改变\n和移动、射击怎样衔接', BLUE), ('退出', '落地、受伤、死亡\n暂停之后如何恢复', GOLD)], '参数引用真实配置，不在每份文档再抄一份。'))
    result.append(triplet('03 · 迭代方式', '先跑一个完整的小闭环', '一次打通一个可观察结果，再逐步扩展',
        [('明确一项改动', '反冲后的动作衔接', GREEN), ('接入真实入口', '控制器 + 镜头 + 表现', BLUE), ('检查再扩展', '正常方向与中断恢复', GOLD)], '先把相关层打通，避免所有模块各自“完成”。'))
    g=base('04 · 给AI一个短入口', 'AGENTS.md：新会话从这里开始', '项目入口负责导航和基本约束，细节按任务读取')
    card(g,'entry',96,365,480,'AGENTS.md','基线 / 读取顺序\n代码边界 / 检查入口',GREEN,.02,h=235)
    for i,(name,body,color) in enumerate([('当前状态','产品现在实际能做什么',BLUE),('任务 + 交接','本次目标、阻塞、下一步',GOLD),('模块 + 相关规范','定位代码、设计与验证',GREEN)]):
        card(g,f'route{i}',930,340+i*128,880,name,body,color,.16+i*.16,h=115,a=(70,0))
        # The single-line cards place body beside the title.
        for e in g['elements'][-3:]:
            if e['type']=='text' and e['y']>340+i*128+70:e.update(x=1320,y=340+i*128+34,width=460,size=30)
    takeaway(g,'先读当前任务及直接依赖，不把全仓历史塞进开场。',.73)
    result.append(g)
    result.append(two('04 · 控制上下文', '改人物，就别先读完整世界观', '以当前player-creator为例 · 按影响范围继续读直接依赖',
        ('本次必要上下文', '人物物理与操作规范\n真实组件、镜头和相关检查', GREEN),
        ('暂时不需要', '所有地区剧情、旧方案\n与本次无关的完整审计', DIM), '短入口负责找到资料，不负责背下全部资料。'))
    result.append(triplet('05 · 固定可复用流程', 'Skills：把经验变成操作步骤', '适用条件 → 所需材料 → 执行 → 验证与交付',
        [('开始前', '读相关规则与真实代码\n明确本次范围', GREEN), ('执行时', '先更新受影响的规范\n再改实现，接入真实场景', BLUE), ('完成后', '运行相关检查\n给出证据和未验范围', GOLD)], 'Skill写得再漂亮，也要靠实际执行确认结果。'))
    result.append(two('05 · 固定可复用流程', '人物Skill，不只写“动作自然”', '当前player-creator正文摘意 · 不是本轮新增成果',
        ('制作要求', '先统一脚底、枪口和附件\n再做完整连续动作', GREEN),
        ('验证要求', '左右朝向、瞄准、反冲衔接\n暂停、死亡和实际镜头', BLUE), '好处：换一次会话，也有明确的工作顺序。'))
    result.append(two('06 · 维护文档', '最想早点加上的一句话', '用户提出的维护原则 · 当前仓库已采用最终交付件式正文',
        ('补丁式追加', '原来A → 后来改B\n特别强调：现在又改C', RED),
        ('直接整理最终稿', '正文只保留当前有效规则\n被替代内容从正文移除', GREEN), '所有文档修改按最终交付件更改，不做补丁式追加。'))
    g=base('06 · 维护文档', '读到最后一句，才知道哪句算数？', '用规则替换演示维护方式；文字为示意，不是历史引文')
    card(g,'old',96,365,810,'旧正文','规则A / 补充B / 再强调C\n读者还得自己解冲突',RED,.02,.46,a=(0,0),b=(-100,0),h=240)
    card(g,'final',96,365,810,'现行正文','统一写清当前规则C\n关联引用一起核对',GREEN,.47,a=(80,0),h=240)
    card(g,'history',1011,365,810,'历史与决策','Git / PR / 必要原件\n可另存简要修订记录',BLUE,.28,h=240)
    takeaway(g,'规范解释现在怎么做；修订记录解释为什么变了。',.74)
    result.append(g)
    result.append(triplet('06 · 每条规则有归属', '别让同一个数值住在三个地方', '当前仓库：设计、配置、任务状态分别维护',
        [('设计正文', '行为与约束\n其他文档链接它', GREEN), ('运行配置', '具体数值\n不再手抄参数表', BLUE), ('任务表', '当前进度\n交接不复制一份状态', GOLD)], '文档一致性靠减少重复定义，不靠到处“再次强调”。'))
    result.append(two('07 · 每次任务怎么跑', '把任务缩到能看懂、能撤回', '这是建议的任务示例，非真实PR或AI聊天截图',
        ('这次做', '反冲动作衔接\n相关规范、实现和验证', GREEN),
        ('这次不扩', '地图生成、美术重制\n和整套成长系统', DIM), '写清改动范围、完成标准与恢复动作。'))
    result.append(triplet('07 · 每次任务怎么跑', '先核对理解，再动手', '小任务也要对齐目标，但不要求每一步都拉人审批',
        [('读', '基线 + 当前任务\n规范 + 真实消费者', GREEN), ('说清', '改哪儿、验什么\n哪里仍然没决定', BLUE), ('做', '设计有变化先改正文\n实现与配置同任务交付', GOLD)], '小范围、完整结果、可审阅差异，方便检查和回退。'))
    result.append(two('07 · 验证与交付', 'CI变短，不等于从此少验', '当前日常CI：project / import / smoke / contracts',
        ('日常基础检查', '快速发现基础错误\n不代表完整功能和体验', BLUE),
        ('按影响选专项', '改移动，检查移动及边界\n改存档，检查恢复与兼容', GREEN), '代码通过、操作体验、手机表现，各自给出依据。'))
    result.append(two('07 · 交接', '“已完成”后面，要能接着干', '当前项目管理规范：一行任务 + 一份当前交接',
        ('任务表维护进度', '目标 / 依赖 / 状态\n链接自己的工作线', GREEN),
        ('交接保留事实', '基线与写集、检查和阻塞\n下一条能继续执行的动作', BLUE), '失败就记失败；缺设备就记未验，不把空白填成通过。'))
    result.append(two('08 · 旧方案怎么退出', '归档，不是看到legacy就全删', '当前架构仍保留明确的旧Provider与正式消费者',
        ('迁移前', '查谁还在引用\n核动态加载、导出和版本', GOLD),
        ('迁移后', '新消费者接通并验证\n再清重复实现与旧入口', GREEN), '历史能追溯，当前入口只指向明确采用的规则。'))
    result.append(two('08 · 管理也需要做减法', '别把开发变成填表比赛', 'PR135已合入：普通任务不强制完整质量卡',
        ('普通修复', '一行任务 + 当前交接\n相关检查即可', GREEN),
        ('新地区 / 新怪物', '按需检查美术与玩法\n只填写适用项', GOLD), '管理材料要帮人继续工作，多一张表也要有用途。'))
    result.append(triplet('09 · 当前真实进展', '规矩写下了，项目还没毕业', '截至本期冻结main · PR134 / PR135已合入',
        [('已整理', '文档职责、短入口\n轻量任务与相关Skills', GREEN), ('仍在做', '地图与正式消费者整合\n对象、剧情及地区缺口', GOLD), ('仍需验证', '长期迭代是否更稳定\n真实手感、设备与趣味', RED)], '管理改动合入，不等于整套游戏和方法论都验收了。'))
    result.append(triplet('把整套方法串起来', '下一次，让AI从明确任务开始', '先有最小清晰规则；再用迭代持续维护',
        [('建项目', '需求 → 架构 → 模块设计', GREEN), ('接任务', 'AGENTS导航 → 相关Skills', BLUE), ('完成一次迭代', '实现 → 检查 → 同步交接', GOLD)], '我想减少的，是每次开工都重新猜一遍。'))
    result.append(two('失序之钟 · 独游折腾记 ep09', '现在补管理，总比继续失控好', '一套仍在实践中的AI项目管理方法',
        ('我这次的建议', '先把规则和边界说清楚\n再让AI持续往前写', GREEN),
        ('也欢迎你来支招', '怎样保持规范不过时？\n哪里还能更简单、更有效？', GOLD), '项目还没做好，先把这次补课过程分享出来。'))
    return result


def main():
    # Written to sound like a personal development diary; no originality or
    # already-proven productivity claim is inferred from external research.
    rows=[
        ('先管项目，再加功能','上一期，我停下新功能，先收拾AI越写越乱的代码仓。这期聊聊怎么管项目。失序之钟还没做好，这套方法也在边用边改。',['user-method','doc-agents']),
        ('三个问题','我的要求其实就三个：这次做什么，哪些地方归谁管，怎么知道做完了。项目变大后，这些信息得让下一个会话也找得到。',['user-method','doc-management']),
        ('需求先行','新建项目，我会先写需求文档。比如反冲跳跃，玩家想获得什么体验，这次改到哪里，怎样算完成。别一上来就让AI建一堆类。',['user-method','doc-game-design','external-spec-kit']),
        ('把完成说清楚','“跳得更爽”太笼统。至少要明确，射击后怎么衔接移动，落地和受伤之后状态对不对，再录连续操作看感觉。检查通过和手感满意，得分开。',['doc-player','doc-development']),
        ('架构不只是文件夹','接着写架构文档：用什么框架，目录怎么组织，模块怎样通信，状态由谁维护。我的游戏用Godot，按功能分模块，应用层把它们接起来。',['doc-architecture','doc-module-map','user-method']),
        ('谁负责执行运动','拿反冲来说，输入负责表达意图，人物运动组件负责真正移动，动画和音效跟着已经接受的事件走。别让表现系统又算出另一套移动规则。',['doc-architecture','doc-player']),
        ('接上真实消费者','新功能也要先找到真实调用入口。否则AI可能写出一个新的统一管理器，旧入口却照跑不误。新旧两套，喜提双倍维护。',['doc-architecture','user-method']),
        ('模块设计','然后写模块设计文档。触发条件、过程衔接，落地、受伤、暂停时怎么退出。数值引用实际配置，别在几份文档里各抄一遍。',['doc-player','doc-agents']),
        ('小闭环迭代','不用一次想完所有细节。选一个小功能，把规则、实现和真实场景打通，检查后再扩展。避免每个模块都说完成，接起来却用不了。',['doc-development','external-small-cls','external-spec-kit']),
        ('AI的项目入口','之后，把入口写进AGENTS文件。新会话先核对基线，看当前状态，找到任务和交接，再按模块导航读取设计与代码。入口要短，细节用链接。',['doc-agents','external-agents-standard']),
        ('按任务加载','改人物动作，就先读人物物理、操作约束和相关代码，没必要先读完所有地区的世界观。上下文有限，得优先留给当前任务和直接依赖。',['doc-agents','doc-player-skill','doc-doc-index']),
        ('Skills固定流程','把重复流程凝结成Skills：什么情况用，先读什么，按什么顺序做，交什么证据。让经验能复用。',['user-method','doc-player-skill','doc-integration-skill']),
        ('用人物Skill举例','比如人物优化，先统一身体、脚底和枪口关系，再做连续动作，核对朝向、瞄准和中断恢复。当然，写在Skill里不等于AI已经做到了，还得检查结果。',['doc-player-skill']),
        ('文档当最终稿维护','还有一句，我真希望最开始就加上：所有文档修改，按照最终交付件的形式更改，不进行补丁式修改和强调。改完通读全文，别只在末尾追加一句最新要求。',['user-method','doc-agents','doc-doc-index']),
        ('现行规则与历史分开','旧规则被替代，就把正文整理成当前最终稿，相关引用也一起改。历史交给Git和PR；需要的话，另外维护简要修订记录，说明改了什么、为什么改。',['user-method','doc-agents','doc-management']),
        ('每条规则只定义一次','同一条规则只在一个地方定义。设计文档讲行为，运行配置管数值，任务表管进度，其他地方引用。到处复制、再强调，只会慢慢长出多个答案。',['doc-agents','doc-doc-index','doc-management']),
        ('把范围圈出来','每次开发，我会把任务切小：这次只改反冲衔接，写清影响范围和完成标准。不要顺手把地图、背包和成长一起重做。改动得小到能看懂，也方便撤回。',['user-method','external-small-cls']),
        ('先对齐再动手','让AI先说明准备改哪儿、怎么验证。有设计取舍就先讨论；设计变了先更新对应正文，再同步实现和配置。原规范已经正确的修复，也不用硬改文档凑流程。',['doc-agents','doc-management','doc-grill']),
        ('验证按影响选择','验证也按影响来。现在仓库日常CI保留四项基础检查，功能改动再选相关专项。基础检查全绿，不代表移动、存档、手机表现和手感都验过。',['doc-agents','doc-current','doc-development']),
        ('可继续的交接','最后，任务表更新进度，当前交接写清基线、改了什么、实际检查、阻塞和下一步。没验就写没验。换个会话，至少能知道从哪儿继续。',['doc-management','doc-agents']),
        ('旧方案退出','旧方案退出，也不能看见legacy就全删。先查还有谁在用，接通新的消费者，验证后再清重复实现。归档可以查历史，不能继续冒充当前开发规则。',['doc-architecture','doc-integration-skill','doc-doc-index']),
        ('别越管越重','管理本身也要做减法。最新整理，普通修复只要一行任务和一份交接；新地区、新怪物，按需要检查美术和玩法。别又变成填表比赛。',['pr135','doc-management','doc-development']),
        ('仍然没做完','这些管理整理已经合入主线，但地图整合、对象设计和体验还有缺口。我现在能说的是，规则和入口更明确了；能不能长期减少返工，还得继续用。',['pr134','pr135','doc-current','doc-data']),
        ('串起整套方法','所以我的顺序是：需求讲目标，架构划边界，设计定行为；入口负责导航，Skills固定流程，再靠小步实现、实际检查和持续更新，把它们连起来。',['user-method','doc-agents','doc-architecture','doc-management']),
        ('边做边改','游戏还没做完，我先补项目管理。你们怎么管理AI大项目？欢迎给我支招。',['user-method','doc-current'])
    ]
    graphics=diagrams()
    assert len(rows)==len(graphics)
    document_ids={
        'AGENTS.md':'doc-agents', 'docs/README.md':'doc-doc-index',
        'docs/project/current_state.md':'doc-current', 'docs/project/project_management.md':'doc-management',
        'docs/project/development.md':'doc-development', 'docs/project/architecture.md':'doc-architecture',
        'docs/project/module_map.md':'doc-module-map', 'docs/project/tasks.md':'doc-tasks',
        'docs/bible/game_design.md':'doc-game-design','docs/bible/player_mechanics.md':'doc-player',
        'docs/data/README.md':'doc-data','.agents/skills/player-creator/SKILL.md':'doc-player-skill',
        '.agents/skills/project-integration/SKILL.md':'doc-integration-skill','.agents/skills/design-grill/SKILL.md':'doc-grill'}
    quotes={
        'doc-agents':['每条规则只定义一次，其余引用。','长期规范按最终交付件维护'],
        'doc-architecture':['Motor 唯一执行运动与碰撞','不要只新增一个无人调用的 helper。'],
        'doc-management':['任务表一行与工作线一份当前交接'],
        'doc-player-skill':['先在正式控制器和真实镜头完成一段连续动作']}
    documents=[]
    for r in json.loads((RESEARCH/'documents.json').read_text()):
        ident=document_ids[r['path']]
        document=dict(r,id=ident,repository='zhipijun1996/gunman-rush',commit=COMMIT,
            url=f'https://raw.githubusercontent.com/zhipijun1996/gunman-rush/{COMMIT}/{r["path"]}',
            page_url=f'https://github.com/zhipijun1996/gunman-rush/blob/{COMMIT}/{r["path"]}',
            verified_quotes=quotes.get(ident,[]),truth='Exact frozen source; document says what is specified, not a new runtime or human acceptance result')
        documents.append(document)
    evidence=[dict(id='user-method',kind='user_testimony_and_editorial_advice',date='2026-11-05',
        text='User requested requirements → architecture including directories/framework → iterative module design; AGENTS入口; Skills流程; final-deliverable document maintenance and optional separate concise revision record. First-person practical recommendations, not claims of invention or proven longitudinal success.')]
    evidence += [dict(d,kind='pinned_repository_document') for d in documents]
    for number in (134,135,136):
        p=json.loads((RESEARCH/f'pr{number}.json').read_text())
        evidence.append(dict(id=f'pr{number}',kind='actual_pr_metadata',url=p['html_url'],title=p['title'],
            head_commit=p['head']['sha'],base_commit=p['base']['sha'],merge_commit=p['merge_commit_sha'],merged_at=p['merged_at'],draft=p['draft'],state=p['state'],
            interpretation='Merged documentation/workflow change is not proof of final game quality; PR136 remains an unmerged draft at scan.'))
    for name in ('spec-kit','small-cls','agents-standard'):
        d=json.loads((RESEARCH/f'{name}.json').read_text())
        evidence.append(dict(d,id='external-'+name,kind='external_method_reference',
            usage={'spec-kit':'Clarify what/why before plan/tasks/code; feature-by-feature iteration, do not force full SDD on bug fixes.',
                   'small-cls':'Self-contained small changes, include real consumer, easier review and rollback.',
                   'agents-standard':'Predictable dedicated agent context/instructions entry.'}[name],
            attribution='Reference retained in sources and posting materials; voice is original personal synthesis. No copied prose, sole-inventor or already-validated experience claim.',
            redistribution='Only URL/hash and our summary delivered; third-party original prose/art not used in visuals or redistributed.'))
    assets=[];shots=[]
    for i,((title,narration,refs),g) in enumerate(zip(rows,graphics),1):
        ident=f'm{i:02}'
        label='方法演示 · 原创动态图示' if i not in (6,13,19,22,23) else '当前仓库规范摘意 · 原创动态图示'
        assets.append(dict(id=ident,origin='editorial',kind='animated_explanatory_diagram',graphic=g,display_label=label,
            license='Original Video Rush vector diagram and wording; MIT. User-authorized game document facts. No third-party illustration, gameplay or voice likeness.',
            truth='Authored explanatory animation. Not captured game, GitHub UI, terminal execution, real PR, or real AI chat. Suggestions and current source facts labeled separately.'))
        shots.append(dict(id=ident,chapter=f'{i:02}',title=title,narration=narration,assets=[ident],offsets=[0],
            presentation='animated_diagram',shot_type='animated_editorial_explanation',transition='cut',
            sfx='pop' if i in (1,7,14,22,25) else None,emphasis='先把项目管起来' if i==1 else '',prs=[],evidence=refs,
            fact_check='Primary source read at frozen SHA. First-person advice is an editorial rendering of the user framework; external enrichment is cited in source/description. No invented empirical benefit, chronology, runtime pass or user acceptance.',
            claim_type='source_grounded_personal_method_and_recommendation_not_proven_success',same_seed_comparison=False))
    previous=json.loads((ROOT/'episodes/ep009.json').read_text())
    cover=base('失序之钟 · 独游折腾记 ep09','AI项目大了，怎么管？','需求 → 架构 → 设计 → 执行与验证')
    cover['elements']=[text(100,105,'失序之钟 · 独游折腾记 ep09',42,GREEN),
        text(100,230,'AI项目越写越乱？',116,WHITE,bold=True),text(100,395,'先把开发规矩立起来',105,GOLD,bold=True),
        text(105,570,'文档先行 · 短入口 · 小步迭代',52,DIM)]
    cover['motion_groups']=[]
    for i,(v,c) in enumerate([('需求与架构',GREEN),('AGENTS + Skills',BLUE),('当前规则唯一',GOLD)]):
        cover['elements'] += [rect(100+590*i,730,550,128,c),text(125+590*i,765,v,48,c,500,bold=True)]
    cover['elements'].append(text(105,955,'仍在打磨中的个人方法 · 原创示意封面',30,DIM))
    title='AI项目越写越乱？我给开发立了几条规矩 | 【失序之钟】独游折腾记 ep09【B站AI创造公开赛】'
    description='''上一期停工重构之后，这期聊聊我准备怎样管理越做越大的AI项目。以《失序之钟》最新主线为例：需求先讲目标与验收；架构划分目录、框架、模块职责与接口；设计落到可观察行为；AGENTS负责短入口，Skills固定可复用流程；每次小范围实现、检查和更新交接。

最想早点加的一条：文档按最终交付件维护，直接整理当前有效正文，不在末尾不断追加补丁和“再次强调”。历史和简要修订记录另外追溯。

游戏和这套方法都还没做完，没有证明能彻底消除返工。画面全部为原创动态解释图，仓库规范与个人建议分开标注；不是游戏录屏或AI真实聊天截图。AI配音，来源冻结于main 48cddb6a；PR134/135已合入，其他待办仍按实际状态判断。

补充阅读与制作资料：
https://github.com/zhipijun1996/video_rush/blob/main/docs/ep010.md
https://github.com/zhipijun1996/gunman-rush
https://github.com/github/spec-kit
https://github.com/agentsmd/agents.md
https://google.github.io/eng-practices/review/developer/small-cls.html

#B站AI创造公开赛# #独立游戏# #AI# #项目管理# #Codex#

分区建议：游戏 / 单机游戏。活动投稿时需关联真实官方话题，标题后缀和文字标签不代替话题选择；用户审片通过前不自动投稿。'''
    spec=dict(schema_version=2,episode='ep010',title=title,
        title_candidates=['让AI持续开发一个大项目，我现在会先做这些 | 【失序之钟】独游折腾记 ep09【B站AI创造公开赛】'],
        repository='zhipijun1996/gunman-rush',asset_spec='episodes/ep010-assets.json',story_ids=['S_AI_PROJECT_METHOD_01'],
        voice='zh-CN-YunxiNeural',rate='+10%',playback_speed=1.04,display_chapters=False,
        editorial_status='source_checked_human_phone_review_pending',music_asset=previous['music_asset'],music_gain=.085,game_audio_gain=0,
        target_duration=[180,300],cover_assets=['m01','m24'],cover=cover,
        research_scope=dict(repository='zhipijun1996/gunman-rush',main_at_scan=COMMIT,scan_date='2026-11-05',
            scope='Targeted update to ep009 complete accessible-history research; current main root/project/bible/skill navigation and14 pinned files personally read, PR134/135 current metadata and PR136 unmerged draft inspected. Not a fresh full-history scan.',
            selected_PRs=[134,135,136],source_document_count=14,
            prior_scope='research/ep009-evidence.json; prior video froze68a87f. This episode rereads latest48cddb and does not reuse previous draft134 status.',
            current_state_internal_baseline='current_state.md itself labels earlier5ce7db; preserved verbatim, not silently updated to scan SHA.',
            game_repo_worktree='Read-only; no game checkout, fetch, edit, engine or test execution.',
            external_references=['github/spec-kit','agentsmd/agents.md','google/eng-practices'],
            limits='Merged documentation/workflow claims checked against exact source. No fresh game runtime, empirical productivity study or long-term method validation. codex getting-started source was a redirect and excluded from substantive references.'),
        evidence=evidence,shots=shots,bilibili_body=description,
        comparison='Explanatory examples and current documentation, no simulated execution or before/after benchmark.',
        comparison_review='图示中现行规范、个人建议和简化示例是否清楚；未声称管理体系已长期验证或游戏已完成。',
        rights=[dict(kind='original_explanatory_diagrams',status='original_project_work_MIT',third_party_images=False),
                dict(kind='user_authorized_repository',status='quoted_facts_from_owned_project_not_blanket_public_license'),
                dict(kind='external_method_research',status='attributed_links_hashes_original_paraphrase_only_no_original_prose_redistributed'),
                dict(kind='music',status=previous['music_asset']['license_status'],source='user supplied the_kindred_hearth; same hash-pinned derivative as earlier authorized films'),
                dict(kind='font',status='Noto CJK SIL OFL1.1'),dict(kind='voice',status='Edge neural synthetic voice, no cloned real-person identity')])
    dump('episodes/ep010-assets.json',dict(schema_version=2,repository=spec['repository'],documents=documents,assets=assets))
    dump('episodes/ep010.json',spec)
    dump('research/ep010-evidence.json',dict(scope=spec['research_scope'],evidence=evidence,
        spoken_external_material='Personal present-tense recommendations, no explicit verbal reference required; source links in description. No fabricated past adoption or exclusive originality.',
        source_documents=documents))
    stories=json.loads((ROOT/'research/stories.json').read_text())
    story=dict(id='S_AI_PROJECT_METHOD_01',event='停工重构后，建立文档分工与轻量AI任务闭环',date='2026-11-04',
        background='AI项目历史规则、文档与流程冗余，用户开始补项目管理。',
        conflict='如何让规则清楚且可接续，同时避免为管理增加重复表格与全量上下文。',
        attempts=['PR134短入口及文档重整','PR135普通任务轻量化、设计与对象规则归属','用户提出需求架构设计与Skills框架'],
        result='文档/流程已合入；游戏内容缺口、长期迭代效果和体验未完成或未验证。',
        truth_status='scoped_workflow_merged_longitudinal_benefit_unverified',evidence_status='exact_current_sources_read',
        commit=COMMIT,base_commit='68a87f38a753442bbdacaa81317dd4aaa05eba3b',pr=135,branch='main',
        linked_sources=[e['url'] for e in evidence if 'url' in e],associated_media=['25 original evidence-linked explanatory animations'],
        recordability='No game footage needed; original diagram animation of document routing, ownership, replacement and task scope.',
        video_potential='User-selected methodology follow-up; practical chain with recoil-jump example; explicitly unfinished.')
    stories=[s for s in stories if s['id']!=story['id']]+[story];dump('research/stories.json',stories)
    script='# '+title+'\n\n制作状态：口播为开发者方法的编辑整理，尚待手机审片。参考出处保留在制作资料；未将外部补充包装为已实践成功或独创。\n\n'
    script+=''.join(f'## {s["id"]} · {s["title"]}\n\n{s["narration"]}\n\n' for s in shots)
    (ROOT/'docs/ep010-script.md').write_text(script)
    print('Authored',len(shots),'shots;',sum(len(s['narration']) for s in shots),'narration characters;',len(documents),'source documents')


if __name__=='__main__':
    main()
