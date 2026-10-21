extends SceneTree
## Existing formal level, one documented initial checkpoint + equipment choice.
## Every later movement, aim and attack goes through original Router/Motor.
var app:DemoApp
var demo:="route_pulse"
var frames:=720
var output:="res://build/route_trace.json"
var rows:Array[Dictionary]=[]
var events:Array[Dictionary]=[]
var failures:Array[String]=[]
var accepted:=0
var seed:="level-design-v2-baseline/08"
var initial:=Vector2.ZERO
var checkpoint:=Vector2.ZERO
var weapon:="pulse_gun"
var trace_start_draw:=0
func _initialize()->void:run.call_deferred()
func pair(v:Vector2)->Array:return[v.x,v.y]
func tick()->void:
 await physics_frame
 if DisplayServer.get_name()!="headless":await RenderingServer.frame_post_draw
func run()->void:
 for a:String in OS.get_cmdline_user_args():
  if a.begins_with("--case="):demo=a.trim_prefix("--case=")
  if a.begins_with("--frames="):frames=int(a.trim_prefix("--frames="))
  if a.begins_with("--output="):output=a.trim_prefix("--output=")
 root.size=Vector2i(1280,720)
 app=preload("res://scenes/demo/demo.tscn").instantiate() as DemoApp;app.meta_persistence_enabled=false;root.add_child(app)
 for i:int in 8:await tick()
 if not app.start_plains(seed):failures.append("start rejected")
 for i:int in 180:
  if app.stage is PlainsRegionStage and app.stage.is_node_ready() and app.stage.assembly_ok and not app._stage_pending:break
  await tick()
 if not app.stage is PlainsRegionStage:quit(1);return
 var c:=app.controller
 var weapons:Dictionary={"route_pulse":"pulse_gun","route_shadow":"shadow_shuriken","route_bomb":"recoil_bomb","route_triple":"triple_machine_gun","route_laser":"sustained_laser","route_fan":"fan_shuriken","route_boomerang":"remote_boomerang","route_mine_combo":"magnetic_mine","route_singularity":"collapse_singularity","singularity_left":"collapse_singularity","combat_pulse":"pulse_gun","combat_laser":"sustained_laser"}
 weapon=weapons[demo]
 checkpoint=Vector2(900,0) if demo in ["route_pulse","route_bomb","route_triple","route_laser","route_singularity"] else Vector2(650,-700)
 if demo in ["route_mine_combo","route_boomerang"]:checkpoint=Vector2(300,-700)
 if demo.begins_with("combat"):checkpoint=Vector2(1190,-700)
 if not c.return_to_segment(checkpoint):failures.append("initial checkpoint rejected")
 if not c.shoot_ability.equip(load("res://resources/weapons/"+weapon+".tres")):failures.append("initial equipment rejected")
 c.air_focus_ability.enabled=false
 c.router.activate_device(&"gamepad")
 for i:int in 60:await tick()
 initial=app.player.global_position
 c.shoot_ability.packet_changed.connect(func(state:StringName,id:int):
  if state==&"started":
   accepted+=1;events.append({"kind":"accepted_packet","frame":rows.size(),"packet":id,"position":pair(app.player.global_position),"direction":pair(c.router.aim_direction),"grounded":app.player.is_on_floor()}))
 c.motor.weapon_blinked.connect(func(a:Vector2,b:Vector2):events.append({"kind":"blink","frame":rows.size(),"from":pair(a),"to":pair(b),"delta":pair(b-a)}))
 c.shoot_ability.behavior().entity_transition.connect(func(e:WeaponEntity,a:StringName):events.append({"kind":str(a),"frame":rows.size(),"point":pair(e.global_position),"actor":pair(app.player.global_position),"direction":pair(e.direction)}))
 c.shoot_ability.behavior().blast_fired.connect(func(p:Vector2):events.append({"kind":"blast","frame":rows.size(),"point":pair(p),"actor":pair(app.player.global_position)}))
 c.energy_recovered.connect(func(amount:float,airborne:bool):events.append({"kind":"energy_recovered","frame":rows.size(),"amount":amount,"airborne":airborne}))
 app.policy.batch_resolved.connect(func(results:Array[DamageResult]):
  for r:DamageResult in results:events.append({"kind":"committed_damage","frame":rows.size(),"amount":r.request.amount,"source":str(r.request.source_id),"target":str(r.request.target_id),"health":r.health.current}))
 trace_start_draw=Engine.get_frames_drawn()
 for f:int in frames:
  await physics_frame
  c.router.activate_device(&"gamepad")
  var aim:=Vector2.DOWN
  var axis:=0.0
  var held:=false
  var jump:=f==20
  var fire:=f==35
  var context:=false
  if demo in ["route_pulse","route_bomb","route_triple","route_laser","route_singularity"]:
   axis=1.0 if f>=20 and f<85 else 0.0
  if demo=="route_shadow":
   aim=Vector2(-.6,1).normalized();axis=1.0 if f>55 and f<90 else 0.0
  if demo=="route_fan":
   aim=Vector2.LEFT if f<51 else Vector2.RIGHT
  if demo=="route_laser":
   held=f>=35 and f<90;fire=false;axis=1.0 if f>=20 and f<130 else 0.0
  if demo=="route_boomerang":
   aim=Vector2(-.8,.6).normalized() if f<43 else Vector2(.8,.6).normalized()
   held=f>=43 and f<70
   axis=-1.0 if f>=45 and f<65 else 0.0
   context=f==70
  if demo=="route_mine_combo":
   jump=f==60;fire=f in [20,110,140];aim=Vector2(.4,1).normalized() if f<40 else Vector2.DOWN
   axis=1.0 if f>=48 and f<67 else 0.0;context=f==83
  if demo=="route_singularity":aim=Vector2.UP if f<50 else Vector2(1,-1).normalized()
  if demo=="singularity_left":aim=Vector2.UP if f<50 else Vector2(-1,-1).normalized()
  if demo.begins_with("combat"):
   jump=f in [20,190];aim=Vector2.RIGHT;axis=-.3 if f>=25 and f<45 else 0.0
   fire=f in [35,75,115,155,205,245]
   if demo=="combat_laser":
    held=(f>=35 and f<65) or (f>=155 and f<185);fire=false
    for b:EnemyMotor in app.stage.enemies:
     var enemy_actor:EnemyActor=b.get_node("Actor")
     if enemy_actor.definition.behavior_id==&"sentry" and not enemy_actor.health.terminal:
      aim=(b.global_position-app.player.global_position).normalized();break
  c.router.set_move_axis(axis);c.router.set_aim(&"gamepad",aim,held)
  if jump:c.router.request_action(&"jump")
  if f in [32,72,202]:c.router.request_action(&"jump_release")
  if fire:c.router.request_action(&"shoot_release",aim)
  if context:c.router.request_action(&"weapon_context")
  if DisplayServer.get_name()!="headless":await RenderingServer.frame_post_draw
  var entities:Array=[]
  for e:WeaponEntity in c.shoot_ability.behavior().current_entities():entities.append({"kind":str(e.kind),"phase":str(e.phase),"position":pair(e.global_position)})
  rows.append({"frame":f,"position":pair(app.player.global_position),"velocity":pair(app.player.velocity),"grounded":app.player.is_on_floor(),"phase":str(c.shoot_ability.behavior().phase),"hp":c.actor_resources.health.current,"stamina":c.actor_resources.stamina.current,"shots":c.action_resources.shot_charges,"epoch":app.lifetime.epoch,"actor_epoch":app.lifetime.actor_epoch,"weapon":weapon,"accepted_shots":accepted,"aim":pair(aim),"move_axis":axis,"entities":entities})
 c.router.clear("video_route_end")
 if accepted<1:failures.append("no accepted attack")
 if rows.any(func(r:Dictionary)->bool:return r.hp<=0 or r.epoch!=rows[0].epoch or r.actor_epoch!=rows[0].actor_epoch):failures.append("death or respawn")
 var slabs:Array=[]
 for r:Rect2 in PlainsRegionScenery.solid_supports(app.stage):slabs.append([r.position.x,r.position.y,r.size.x,r.size.y])
 var receipt:Dictionary={"case":demo,"weapon":weapon,"seed":seed,"manifest_hash":app.stage.generated.manifest.manifest_hash,"frames":rows,"events":events,"failures":failures,"accepted_shots":accepted,"trace_start_draw":trace_start_draw,"initial_position":pair(initial),"checkpoint":pair(checkpoint),"actual_supports":slabs,"initialization":"Existing formal map with one initial checkpoint through return_to_segment + equip; normal-speed optional focus off; original Router/Motor, AI/collision/resources unchanged thereafter","no_midflight_position_health_resource_injection":true,"scope":"Positioned formal-level action/combat window, not a natural unlock, full route or campaign completion"}
 DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output.get_base_dir()))
 var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(receipt));file.close();app.free();await process_frame
 print("ROUTE CAPTURE ",demo," ",accepted," attacks ",failures);quit(0 if failures.is_empty() else 1)
