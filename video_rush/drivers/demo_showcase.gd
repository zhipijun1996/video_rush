extends SceneTree
## Selected independent formal-room excerpts. One disclosed starting pose per
## take, then only the existing Router, interaction and dialogue controls.
var app: FixedWorldApp
var output := "user://demo-showcase.json"
var take := "p10"
var source_commit := ""
const PATROL_PILOT=preload("res://tools/bellstrider_01/legal_input_pilot.gd")
class StageFacade extends Node2D:
 var boss: BossMotor
 var boss_arena: Rect2
class AppFacade extends Node:
 var player: PlayerMotor
 var controller: PlayerController
 var stage: StageFacade
 var _boss_started := false
var pilot: RefCounted
var facade: AppFacade
var rows: Array = []
var events: Array = []
var failures: Array = []
var tracking := false
var first_frame := 0
var entry_session := 0
var entry_hp := 0.0
var initial_pose := Vector2.ZERO

func _initialize() -> void: run.call_deferred()
func ticks(n: int) -> void:
 for i: int in n: await physics_frame
func point(v: Vector2) -> Array: return [v.x,v.y]
func mark(kind: String, extra: Dictionary = {}) -> void:
 var row := {"event":kind,"movie_frame":Engine.get_process_frames(),"take_frame":Engine.get_process_frames()-first_frame}
 row.merge(extra);events.append(row);print("SHOWCASE ",JSON.stringify(row))
func check(ok: bool, label: String) -> void:
 mark("check",{"ok":ok,"label":label,"position":point(app.player.position)})
 if not ok: failures.append(label)
func sample() -> void:
 if not tracking or app.busy or not is_instance_valid(app.player) or not is_instance_valid(app.controller) or not is_instance_valid(app.story): return
 rows.append({"frame":Engine.get_process_frames(),"room":app.room.room_id,"position":point(app.player.position),"grounded":app.player.is_on_floor(),"velocity":point(app.player.normal_velocity+app.player.recoil_velocity),"ammo":app.controller.action_resources.shot_charges,"hp":app.controller.actor_resources.health.current,"session":app.controller.session_id,"axis":app.controller.router.axis,"story":app.story.active,"story_line":app.story.line_index,"story_phase":app.story.phase,"time_scale":Engine.time_scale})
 if take=="patrol" and app.room.encounter!=null:
  var boss:=app.room.encounter as BellstriderEncounter
  rows[-1].merge({"boss_hp":boss.health.current,"boss_mode":str(boss.mode),"boss_position":point(boss.motor.position),"boss_metrics":boss.combat_metrics()})
func walk(x: float, budget: int = 180) -> void:
 for frame: int in budget:
  if absf(app.player.position.x-x)<6: break
  app.controller.router.set_source_axis(&"keyboard_mouse",clampf((x-app.player.position.x)/26.0,-1,1))
  await ticks(1)
 app.controller.router.set_source_axis(&"keyboard_mouse",0)
 await ticks(5)
 check(absf(app.player.position.x-x)<16,"walk to "+str(x))
func jump() -> void:
 app.controller.router.set_jump_held(&"keyboard_mouse",false)
 await ticks(2)
 app.controller.router.set_jump_held(&"keyboard_mouse",true)
 mark("jump_requested")
func land(target: Vector2, budget: int = 150, hold: int = 24) -> void:
 for frame: int in budget:
  await ticks(1)
  app.controller.router.set_source_axis(&"keyboard_mouse",clampf((target.x-app.player.position.x)/35.0,-1,1))
  if app.player.is_on_floor(): break
 app.controller.router.clear("landed")
 check(app.player.is_on_floor() and absf(app.player.position.y-target.y)<6,"land "+str(target))
 await ticks(hold)
func fire(aim: Vector2, label: String) -> void:
 app.controller.router.request_action(&"shoot_release",aim.normalized())
 mark("shot_requested",{"aim":point(aim.normalized()),"label":label})
func hit(id: String) -> void:
 var enemy: EnemyActor = app.room.enemies[id]
 var before := enemy.health.current
 fire(enemy.motor.position-app.player.position-Vector2(0,-6),id)
 await ticks(16)
 check(enemy.health.current<before and app.controller.action_resources.shot_charges==1 and not app.player.is_on_floor(),"native hit refills air shot: "+id)
func hop(target: Vector2, aim: Vector2, delay: int = 16) -> void:
 app.controller.router.set_source_axis(&"keyboard_mouse",signf(target.x-app.player.position.x))
 await jump();await ticks(delay)
 if aim!=Vector2.ZERO:fire(aim,"recoil hop")
 await land(target)
func p10() -> void:
 mark("lesson_one")
 await walk(896)
 app.controller.router.set_source_axis(&"keyboard_mouse",1)
 await jump();await ticks(18)
 app.controller.router.set_source_axis(&"keyboard_mouse",0)
 await hit("P-R10:r9:teach_down")
 fire(Vector2.DOWN,"second downward recoil")
 await land(Vector2(1056,1678))
 if not failures.is_empty():return
 mark("lesson_two")
 await walk(1296);await jump();await ticks(22)
 await hit("P-R10:r9:teach_diagonal")
 fire(Vector2.DOWN,"turn aim down after diagonal hit")
 await land(Vector2(1120,1326))
 if not failures.is_empty():return
 await walk(896);mark("four_shot_chain")
 await jump();await ticks(22)
 await hit("P-R10:r9:combo_left")
 await hit("P-R10:r9:combo_down")
 await hit("P-R10:r9:combo_right")
 fire(Vector2.DOWN,"fourth recoil crosses 608-height gap")
 await land(Vector2(960,718))
 if not failures.is_empty():return
 await walk(960);mark("final_ascent")
 await hop(Vector2(896,430),Vector2.DOWN)
 await walk(832);app._interact();mark("reward_interaction");await ticks(90)
 await hop(Vector2(768,142),Vector2.DOWN)
 check(app.player.position.y<160,"base gun reaches upper exit ledge")
 await ticks(100)
func clockheart() -> void:
 await walk(1536);app._interact();mark("enter_clockheart")
 for i: int in 240:
  await ticks(1)
  if app.room.room_id=="Z-R01" and not app.busy:break
 check(app.room.room_id=="Z-R01","actual P33 door enters clockheart")
 await walk(465);await ticks(150)
 check(app.story.active,"native clockheart story starts")
 for i: int in 3:
  mark("dialogue",{"index":i,"text":app.story._lines()[i]})
  await ticks(235 if i!=1 else 275)
  app.story.advance();await ticks(5)
 await ticks(90)
 check(app.state.has("clockheart_briefed"),"actual investigation commits permission")
func street() -> void:
 await walk(1300,400)
 await ticks(90)
 app.show_map();mark("native_explored_map");await ticks(170)
 app._close_panel();await ticks(40)
func windmill() -> void:
 fire(Vector2(224,320)-app.player.position-Vector2(0,-6),"shoot actual windmill bell")
 await ticks(35)
 check((app.room.get_node("Carrier0") as WorldMovingPlatform).motion_running,"native bell drives carrier")
 await hop(Vector2(400,526),Vector2(-.8,.6))
 await ticks(150)
func carrier() -> void:
 await hop(Vector2(960,1332),Vector2.ZERO)
 fire(Vector2(960,1280)-app.player.position,"start west hoist from real deck")
 await ticks(20)
 var lift:=app.room.get_node("Carrier0") as WorldMovingPlatform
 check(lift.motion_running,"actual bullet starts west carrier")
 for i:int in 650:
  await ticks(1)
  if lift.position.y<=864.1:break
 check(app.player.is_on_floor() and absf(app.player.position.y-836)<4,"native west hoist reaches top with player")
 await walk(1008)
 await hop(Vector2(1280,686),Vector2(-.4,.916515))
 await ticks(100)
func dual_carriers() -> void:
 await carrier()
 await walk(1760,260)
 await hop(Vector2(1936,596),Vector2.ZERO)
 fire(Vector2(1936,544)-app.player.position,"start real diagonal carrier")
 await ticks(20)
 var lift:=app.room.get_node("Carrier1") as WorldMovingPlatform
 check(lift.motion_running,"actual shot starts diagonal carrier")
 for i:int in 650:
  await ticks(1)
  if lift.position.y<=384.1:break
 check(app.player.is_on_floor() and absf(app.player.position.y-356)<4,"native diagonal carrier reaches top")
 await walk(2192)
 await hop(Vector2(2112,142),Vector2.DOWN)
 await ticks(90)
func broken_bridge() -> void:
 await hop(Vector2(1184,910),Vector2.RIGHT)
 await walk(1000);await hop(Vector2(672,910),Vector2.RIGHT)
 await walk(608);await hop(Vector2(640,686),Vector2.DOWN)
 await walk(736);await hop(Vector2(928,558),Vector2(-.4,.916515))
 await walk(1088);await hop(Vector2(1168,366),Vector2.DOWN)
 await walk(1200);await hop(Vector2(1344,142),Vector2.DOWN)
 await ticks(90)
func thorn_route() -> void:
 await hop(Vector2(4672,1902),Vector2(.8,.6))
 await walk(4368,220);await hop(Vector2(4080,2062),Vector2(.8,-.6),10)
 await walk(3744,240);await hop(Vector2(3440,2030),Vector2.RIGHT)
 await walk(2960,300)
 app.controller.router.set_source_axis(&"keyboard_mouse",-1)
 for i:int in 60:
  await ticks(1)
  if app.player.position.y>=2140:break
 fire(Vector2.RIGHT,"horizontal recoil below narrow thorn roof")
 for i:int in 100:
  await ticks(1)
  if app.player.position.x<2624:app.controller.router.set_source_axis(&"keyboard_mouse",0)
  if app.player.is_on_floor():break
 app.controller.router.clear("thorn route finish")
 check(app.player.is_on_floor() and app.player.position.x<2680 and absf(app.player.position.y-2222)<5,"continuous thorn route reaches final bank")
 await ticks(90)
func cellar() -> void:
 await jump();await ticks(12)
 fire(Vector2(920,592)-app.player.position-Vector2(0,-6),"shoot cellar shutter bell in the air")
 var opened:=false
 for i:int in 100:
  await ticks(1)
  opened=opened or app.room.mechanisms["P-R12:air_shutter"].is_open
  if app.player.position.y<430:app.controller.router.set_source_axis(&"keyboard_mouse",1)
  if app.player.position.x>1053:app.controller.router.set_source_axis(&"keyboard_mouse",0)
  if app.player.is_on_floor():break
 app.controller.router.clear("cellar gate")
 check(opened and app.player.is_on_floor() and app.player.position.x>992 and absf(app.player.position.y-462)<5,"actual shutter shot and upward crossing")
 await walk(1104);app._interact();mark("native_cellar_reward");await ticks(90)
func well_route() -> void:
 for target_y:float in [1806.0,1678.0]:
  await jump();await ticks(24);app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(48)
  check(app.player.is_on_floor() and absf(app.player.position.y-target_y)<5,"native well climb "+str(target_y))
 await walk(1152)
 await meadow()
func patrol() -> void:
 pilot=PATROL_PILOT.new();facade=AppFacade.new();facade.player=app.player;facade.controller=app.controller
 facade.stage=StageFacade.new();facade.stage.boss=app.room.boss;facade.stage.boss_arena=app.room.arena_bounds
 var boss:=app.room.encounter as BellstriderEncounter
 var initial:=boss.health.current
 var units:Array[Dictionary]=[]
 mark("native_boss_excerpt_start",{"boss_hp":initial,"kind":"unmodified live battle excerpt; no defeat claim"})
 for i:int in 1440:
  facade._boss_started=app.room.battle_started
  pilot.step(facade,boss,boss.combat_metrics(),units)
  await ticks(1)
  if app.controller.actor_resources.health.current<=0 or app.room.room_id!="P-R11":break
  if boss.health.terminal:mark("native_boss_defeated");await ticks(120);break
 app.controller.router.clear("patrol excerpt end")
 check(app.room.battle_started and boss.health.current<initial,"actual patrol battle begins and accepts player damage")
 facade.stage.free();facade.free()
func fight(id: String) -> void:
 var enemy:EnemyActor=app.room.enemies[id]
 for i:int in 160:
  if enemy.health.terminal:break
  if i%20==0:fire(enemy.motor.position-app.player.position-Vector2(0,-6),"fight "+id)
  await ticks(1)
 check(enemy.health.terminal,"native enemy defeated: "+id)
func secret_route() -> void:
 mark("secret_approach",{"concealed":app.room.camera_concealers.secret.visible})
 await walk(1984)
 await fight("P-R26:review06:chest_patrol")
 await walk(2240);app._interact();await ticks(90)
 check(not app.room.camera_concealers.secret.visible,"walking through plants actually reveals hidden room")
 check(app.state.value.receipts.has("open_P26_hidden_chest"),"real hidden chest opened")
func long_bridge() -> void:
 await hop(Vector2(2224,772),Vector2.ZERO)
 fire(Vector2(1952,744)-app.player.position-Vector2(0,-6),"start actual bridge inspection carrier")
 await ticks(25)
 var lift:=app.room.get_node("BridgeInspectionLift") as WorldMovingPlatform
 check(lift.motion_running,"actual bell starts bridge inspection lift")
 for i:int in 650:
  await ticks(1)
  if lift.position.y<=640.1:break
 check(app.player.is_on_floor() and absf(app.player.position.y-612)<5,"real inspection carrier arrives")
 await hop(Vector2(2496,622),Vector2.ZERO)
 mark("native_clockheart_vista");await ticks(150)
func water_carrier() -> void:
 await hop(Vector2(2240,1348),Vector2.ZERO)
 fire(Vector2(2048,1376)-app.player.position-Vector2(0,-6),"activate real irrigation cage")
 await ticks(25)
 var lift:=app.room.get_node("IrrigationCage") as WorldMovingPlatform
 check(lift.motion_running,"actual bell activates irrigation cage")
 for i:int in 650:
  await ticks(1)
  if lift.position.y<=864.1:break
 check(app.player.is_on_floor() and absf(app.player.position.y-836)<5,"irrigation cage carries player to upper level")
 await hop(Vector2(2240,686),Vector2.ZERO)
 await ticks(120)
func hang(target: Vector2, first: bool = false) -> void:
 if first:await jump();await ticks(16)
 else:
  app.controller.router.set_jump_held(&"keyboard_mouse",false)
  app.controller.router.set_source_axis(&"keyboard_mouse",signf(target.x-app.player.position.x))
  await jump();await ticks(18)
 app.controller.router.request_action(&"grapple",(target-app.player.position-Vector2(0,-6)).normalized())
 for i:int in 100:
  await ticks(1)
  if app.controller.traversal.state==&"hook_hang" and app.player.position.distance_to(target)<65:break
 check(app.controller.traversal.state==&"hook_hang" and app.player.position.distance_to(target)<65,"actual grapple hang: "+str(target))
 mark("native_hook_hang",{"anchor":point(target),"position":point(app.player.position)})
 app.controller.router.set_source_axis(&"keyboard_mouse",0)
 app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(20)
func hook_route() -> void:
 await hang(Vector2(1200,680),true)
 await jump();await ticks(20)
 await land(Vector2(1104,622))
 await hang(Vector2(960,416),true)
 await hang(Vector2(960,224))
 await jump();await ticks(20);await land(Vector2(960,142))
 await ticks(100)
func meadow() -> void:
 app.controller.router.set_source_axis(&"keyboard_mouse",-1)
 await jump();await ticks(16);fire(Vector2(.65,.76),"recoil onto meadow choice platform")
 await land(Vector2(880,1454),150,0)
 var target:EnemyActor=app.room.enemies["P-R06:low_flight"]
 mark("native_enemy_exchange")
 for i:int in 180:
  if is_instance_valid(target) and not target.health.terminal and i%14==0:
   fire(target.motor.position-app.player.position-Vector2(0,-6),"respond to actual diving enemy")
  await ticks(1)
func sluice() -> void:
 app.controller.router.set_source_axis(&"keyboard_mouse",-1)
 for i:int in 60:
  await ticks(1)
  if app.player.position.x<=2240 and app.player.position.y>=998:break
 fire(Vector2(2360,1088)-app.player.position-Vector2(0,-6),"falling shot opens sluice while recoiling through")
 var opened:=false
 for i:int in 100:
  await ticks(1)
  opened=opened or app.room.mechanisms["P-R20:r8:sluice"].is_open
  if app.player.position.x<2024:app.controller.router.set_source_axis(&"keyboard_mouse",0)
  if app.player.is_on_floor():break
 app.controller.router.clear("sluice reached")
 check(opened and app.player.is_on_floor() and app.player.position.x<2080,"actual falling shot, sluice opening and passage")
 await ticks(160)
func repair() -> void:
 await walk(1952)
 app._interact();mark("native_clock_repair_interaction")
 await ticks(350)
 check(app.story.active,"native clock repair sequence")
 for i: int in 2:
  mark("dialogue",{"index":i,"text":app.story._lines()[i]})
  await ticks(210);app.story.advance();await ticks(5)
 await ticks(100)
 check(app.state.has("clock_P"),"repair receipt committed")
func run() -> void:
 for arg: String in OS.get_cmdline_user_args():
  if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
  if arg.begins_with("--case="):take=arg.trim_prefix("--case=")
  if arg.begins_with("--source-commit="):source_commit=arg.trim_prefix("--source-commit=")
 if source_commit.length()!=40:printerr("Exact source commit required");quit(2);return
 root.size=Vector2i(1280,720)
 app=preload("res://game/application/world/fixed_world.tscn").instantiate()
 app.save_path="user://demo_showcase_"+take+".json";root.add_child(app)
 await ticks(5)
 var config: Dictionary={
  "p10":{"room":"P-R10","pose":Vector2(896,2030),"stage":"base"},
  "clockheart":{"room":"P-R33","pose":Vector2(1330,558),"stage":"base"},
  "street":{"room":"P-R01","pose":Vector2(900,1262),"stage":"base"},
  "windmill":{"room":"P-R05","pose":Vector2(192,366),"stage":"base"},
  "repair":{"room":"P-R15","pose":Vector2(1800,3918),"stage":"h"},
  "carrier":{"room":"P-R26","pose":Vector2(800,1390),"stage":"base"},
  "meadow":{"room":"P-R06","pose":Vector2(1152,1678),"stage":"base"},
  "sluice":{"room":"P-R20","pose":Vector2(2352,942),"stage":"base"},
  "dual_carriers":{"room":"P-R26","pose":Vector2(800,1390),"stage":"base"},
  "broken_bridge":{"room":"P-R04","pose":Vector2(1512,910),"stage":"base"},
  "thorn_route":{"room":"P-R13","pose":Vector2(5032,2062),"stage":"base"},
  "cellar":{"room":"P-R12","pose":Vector2(928,686),"stage":"base"},
  "well_route":{"room":"P-R06","pose":Vector2(1216,1934),"stage":"base"},
  "patrol":{"room":"P-R11","pose":Vector2(400,1134),"stage":"h"},
  "secret_route":{"room":"P-R26","pose":Vector2(1800,1518),"stage":"base"},
  "long_bridge":{"room":"P-R32","pose":Vector2(2096,814),"stage":"base"},
  "hook_route":{"room":"P-R32","pose":Vector2(1184,942),"stage":"h"},
  "water_carrier":{"room":"P-R18","pose":Vector2(2080,1422),"stage":"base"}}
 if not config.has(take):quit(2);return
 var recipe: Dictionary=config[take]
 await app.review.begin(recipe.room,"",recipe.stage)
 initial_pose=recipe.pose;app.player.reset_at(initial_pose)
 (app.camera as WorldCamera).reset_view()
 await ticks(50)
 entry_session=app.controller.session_id;entry_hp=app.controller.actor_resources.health.current
 app.controller.shoot_ability.shot_fired.connect(func(aim:Vector2,id:int)->void:mark("native_shot",{"id":id,"aim":point(aim),"position":point(app.player.position),"ammo":app.controller.action_resources.shot_charges}))
 first_frame=Engine.get_process_frames();tracking=true;physics_frame.connect(sample)
 mark("take_start",{"room":recipe.room,"initial_pose":point(initial_pose),"stage":recipe.stage,"invincible":app.review.invincible,"kind":"independent formal review; one initial pose, then original native inputs"})
 await ticks(50)
 match take:
  "p10":await p10()
  "clockheart":await clockheart()
  "street":await street()
  "windmill":await windmill()
  "repair":await repair()
  "carrier":await carrier()
  "meadow":await meadow()
  "sluice":await sluice()
  "dual_carriers":await dual_carriers()
  "broken_bridge":await broken_bridge()
  "thorn_route":await thorn_route()
  "cellar":await cellar()
  "well_route":await well_route()
  "patrol":await patrol()
  "secret_route":await secret_route()
  "long_bridge":await long_bridge()
  "hook_route":await hook_route()
  "water_carrier":await water_carrier()
 var expected_changes:=1 if take=="clockheart" else 0
 check(app.controller.session_id==entry_session+expected_changes,"only expected room-transition session changes; no respawn")
 mark("take_end");tracking=false
 var file:=FileAccess.open(output,FileAccess.WRITE)
 file.store_string(JSON.stringify({"case":take,"source_commit":source_commit,"initial_pose":point(initial_pose),"frames":rows,"events":events,"failures":failures,"native_inputs_only_after_initial_pose":true,"enemy_AI_unchanged":true,"health_override":false,"resource_override":false,"human_play":false,"complete":failures.is_empty()},"  "));file.close()
 await WorldAudioLifecycle.drain_world(app);quit(0 if failures.is_empty() else 1)
