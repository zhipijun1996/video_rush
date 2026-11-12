extends SceneTree
## Selected independent formal-room excerpts. One disclosed starting pose per
## take, then only the existing Router, interaction and dialogue controls.
var app: FixedWorldApp
var output := "user://demo-showcase.json"
var take := "p10"
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
  "sluice":{"room":"P-R20","pose":Vector2(2352,942),"stage":"base"}}
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
 var expected_changes:=1 if take=="clockheart" else 0
 check(app.controller.session_id==entry_session+expected_changes,"only expected room-transition session changes; no respawn")
 mark("take_end");tracking=false
 var file:=FileAccess.open(output,FileAccess.WRITE)
 file.store_string(JSON.stringify({"case":take,"source_commit":"dec47408ce8b7c4b98c5e215c8a23db482bc7864","initial_pose":point(initial_pose),"frames":rows,"events":events,"failures":failures,"native_inputs_only_after_initial_pose":true,"enemy_AI_unchanged":true,"health_override":false,"resource_override":false,"human_play":false,"complete":failures.is_empty()},"  "));file.close()
 await WorldAudioLifecycle.drain_world(app);quit(0 if failures.is_empty() else 1)
