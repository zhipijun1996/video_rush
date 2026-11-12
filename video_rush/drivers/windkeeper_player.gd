extends SceneTree
## PR150 recorder: source-owned aiming/occlusion helpers, ordinary inputs,
## half-second real focus before each airborne shot, walk-off/recoil phase III.
const SOURCE_PILOT = preload("res://tools/windkeeper_pressure_01/legal_input_pilot.gd")
class StageView extends Node2D:
	var boss: BossMotor
class AppView extends Node:
	var player: PlayerMotor
	var stage: StageView

var app: FixedWorldApp
var boss: WindkeeperPressureEncounter
var pilot: RefCounted
var view: AppView
var stage_view: StageView
var output := "user://windkeeper-player.json"
var frame := 0
var phase3_admitted := false
var corner_reset := false
var corner_done := false
var corner_boosted := false
var corner_side := 0
var corner_origin := Rect2()
var start_movie := 0
var rows: Array = []
var events: Array = []
var shots: Array = []
var pending: Dictionary = {}
var release_focus: Dictionary = {}
var air_shots := 0
var initial_session := -1
var initial_hp := 0.0
var initial_boss_hp := 0.0
var last_phase := 0
var last_state := ""
var failure := ""
var victory := -1
var phase3_goal := Vector2.INF
var phase3_origin := Rect2()
var phase3_crossing := false
var phase3_boosted := false
var cross_begin := -1
var last_ground_shot := -1000
var jump_release := -1
var active := false
var budget := 30000
var heal_until := -1
var mount_goal := Vector2.INF

func _initialize() -> void: run.call_deferred()
func ticks(n: int) -> void:
	for i: int in n: await physics_frame
func event(kind: String,extra: Dictionary={}) -> void:
	var row := {"event":kind,"frame":frame,"movie_frame":Engine.get_process_frames()-start_movie}
	row.merge(extra);events.append(row)
	if kind in ["phase","victory","failed","cross_begin","cross_landed"]:print("WINDKEEPER ",JSON.stringify(row))
func point(v: Vector2) -> Array: return [v.x,v.y]
func request_shot(aim: Vector2,reason: String) -> bool:
	if not pending.is_empty() or app.controller.shoot_ability.cooldown_remaining>0 or app.controller.action_resources.shot_charges<=0:return false
	if app.controller.shot_energy!=null and not app.controller.shot_energy.can_fire():return false
	if app.player.is_on_floor():
		if not app.controller.router._jump_sources.is_empty():return false
		if (boss.stage_phase==1 and boss.health.current<=boss.health.capacity*boss.definition.phase_two_health) or (boss.stage_phase==2 and boss.health.current<=boss.health.capacity*boss.definition.phase_three_health):return false
		release_focus={};last_ground_shot=frame
		event("ground_release",{"aim":point(aim),"reason":reason})
		return app.controller.router.request_action(&"shoot_release",aim.normalized())
	if air_shots>=1 or app.controller.air_focus_ability.stamina<25:return false
	pending={"aim":aim.normalized(),"reason":reason,"focus_start":-1,"began":frame,"cross_begin":cross_begin if reason=="phase3_walk_off_recoil" else -1}
	app.controller.router.set_aim(&"keyboard_mouse",aim.normalized(),true)
	event("aim_begin",{"aim":point(aim),"reason":reason})
	return true
func focus_step() -> void:
	if pending.is_empty():return
	var focus:=app.controller.air_focus_ability
	if app.player.is_on_floor() or frame-int(pending.began)>100:
		event("aim_cancel",{"reason":"landed or bounded focus timeout"});pending.clear();app.controller.router.set_aim(&"keyboard_mouse",Vector2.RIGHT,false);return
	app.controller.router.set_aim(&"keyboard_mouse",pending.aim,true)
	var movie:=Engine.get_process_frames()-start_movie
	if focus.active and int(pending.focus_start)<0:pending.focus_start=movie
	if focus.active and int(pending.focus_start)>=0 and movie-int(pending.focus_start)>=30:
		release_focus={"start":pending.focus_start,"end":movie,"frames":movie-int(pending.focus_start),"reason":pending.reason,"cross_begin":pending.cross_begin}
		event("air_release",{"focus":release_focus.duplicate(),"aim":point(pending.aim)})
		app.controller.router.request_action(&"shoot_release",pending.aim)
		app.controller.router.set_aim(&"keyboard_mouse",pending.aim,false)
		pending.clear()
func shot_fired(aim: Vector2,id: int) -> void:
	var airborne:=not app.player.is_on_floor()
	if airborne:air_shots+=1
	shots.append({"id":id,"frame":frame,"movie_frame":Engine.get_process_frames()-start_movie,"airborne":airborne,"flight_ordinal":air_shots if airborne else 0,"focus":release_focus.duplicate(),"aim":point(aim),"position":point(app.player.position),"phase":boss.stage_phase})
	release_focus={}
func support(at: Vector2,ground_only: bool=true) -> Rect2:
	if ground_only and not app.player.is_on_floor():return Rect2()
	for rect: Rect2 in boss._support_rects:
		if at.x>=rect.position.x-12 and at.x<=rect.end.x+12 and absf(at.y+18-rect.position.y)<8:return rect
	return Rect2()
func ground_safe(aim: Vector2) -> bool:
	var at:=app.player.position
	var tuning:=app.player.tuning
	var distance:=tuning.shot_burst_speed*tuning.shot_burst_duration*tuning.ground_recoil_multiplier+2
	var finish:=at-aim.normalized()*distance
	for amount: float in [0.0,.5,1.0]:
		var foot:=Vector2(lerpf(at.x,finish.x,amount),at.y+17)
		var query:=PhysicsRayQueryParameters2D.create(foot,foot+Vector2(0,35),1,[app.player.get_rid()])
		if app.player.get_world_2d().direct_space_state.intersect_ray(query).is_empty():return false
	return true
func start_cross(slab: Rect2,reason: String) -> void:
	var at:=app.player.position
	var best:=INF
	var target:=Vector2.INF
	for rect: Rect2 in boss._support_rects:
		if rect==slab:continue
		var p:=Vector2(rect.get_center().x,rect.position.y-18)
		var distance:=absf(p.x-at.x)
		if distance>450:continue
		var value:=distance+maxf(0,180-absf(p.x-boss.motor.global_position.x))*3
		if value<best:best=value;target=p
	if not target.is_finite():return
	phase3_goal=target;phase3_origin=slab;phase3_crossing=true;phase3_boosted=false;cross_begin=frame
	app.controller.router.set_jump_held(&"keyboard_mouse",false)
	event("cross_begin",{"from":point(at),"goal":point(target),"origin_rect":[slab.position.x,slab.position.y,slab.size.x,slab.size.y],"boss_state":str(boss.mode),"reason":reason,"method":"walk off actual shelf; one focused recoil; no takeoff jump"})
func phase3_step() -> void:
	var at:=app.player.position
	var router:=app.controller.router
	var slab:=support(at)
	var metrics:=boss.combat_metrics()
	var state:=str(boss.mode)
	var hop: Rect2=metrics.get("hop_target_rect",Rect2())
	if not corner_done and not corner_reset and slab.size.x>0 and int(boss._boundary_escape_side)!=0:
		corner_reset=true;corner_side=int(boss._boundary_escape_side);corner_origin=slab
		event("corner_pressure_reset_begin",{"position":point(at),"arena":[boss.arena.left_x,boss.arena.right_x]})
	if corner_reset:
		var edge: float=boss.arena.right_x-boss.definition.boundary_escape_rearm_distance-12 if corner_side>0 else boss.arena.left_x+boss.definition.boundary_escape_rearm_distance+12
		if not corner_boosted:
			router.set_source_axis(&"keyboard_mouse",-corner_side);router.set_jump_held(&"keyboard_mouse",false)
			if not app.player.is_on_floor() and (at.x-edge)*corner_side<0 and at.y+18-corner_origin.position.y>=24:
				corner_boosted=request_shot(Vector2(-corner_side*.75,1),"return_from_corner_pressure_readjustment")
				if corner_boosted:router.set_source_axis(&"keyboard_mouse",corner_side)
		else:
			var goal:=corner_origin.get_center().x-corner_side*25
			router.set_source_axis(&"keyboard_mouse",signf(goal-at.x) if absf(goal-at.x)>7 else 0)
			if slab.size.x>0 and app.player.is_on_floor():corner_reset=false;corner_done=true;event("corner_pressure_reset_landed",{"position":point(at),"boundary_side":boss._boundary_escape_side})
		return

	if slab.size.x>0:phase3_admitted=true
	if not phase3_crossing and slab.size.x>0:
		var comes_here:=hop.size.x>0 and hop.intersects(slab) and state in ["traverse","lunge","retreat"]
		var crowded:=absf(at.x-boss.motor.global_position.x)<170 and state in ["approach","turn","stomp_warning","sweep_warning"]
		if comes_here or crowded:start_cross(slab,"read the incoming locked Boss jump" if comes_here else "leave the close occupied shelf")
	if phase3_crossing:
		heal_until=-1;router.set_focus_heal_held(&"keyboard_mouse",false)
		var dx:=phase3_goal.x-at.x
		router.set_source_axis(&"keyboard_mouse",signf(dx) if absf(dx)>7 else 0)
		router.set_jump_held(&"keyboard_mouse",false)
		if not app.player.is_on_floor() and not phase3_boosted:
			var drop:=at.y+18-phase3_origin.position.y
			var boss_jumping: bool=bool(metrics.get("airborne",false))
			if drop>=32 or (boss_jumping and drop>=18):
				phase3_boosted=request_shot(Vector2(-signf(dx)*.75,1),"phase3_walk_off_recoil")
				if phase3_boosted:event("walk_off",{"position":point(at),"goal":point(phase3_goal),"cross_begin":cross_begin})
		if app.player.is_on_floor() and slab.size.x>0 and slab!=phase3_origin and absf(at.x-phase3_goal.x)<100:
			event("cross_landed",{"position":point(at),"goal":point(phase3_goal),"boosted":phase3_boosted,"cross_begin":cross_begin});phase3_crossing=false;phase3_goal=Vector2.INF
		elif frame-cross_begin>220:
			event("cross_timeout",{"position":point(at)});phase3_crossing=false
		return
	# Mount an actual support with normal jump/recoil before the warning thorns.
	if slab.size.x==0:
		if not mount_goal.is_finite() and int(boss._boundary_escape_side)==1:mount_goal=Vector2(1118,612)
		if not mount_goal.is_finite():
			var distance:=INF
			for rect: Rect2 in boss._support_rects:
				var p:=Vector2(rect.get_center().x,rect.position.y-18)
				if absf(p.x-boss.motor.global_position.x)<170:continue
				if at.distance_squared_to(p)<distance:distance=at.distance_squared_to(p);mount_goal=p
		if mount_goal.is_finite():
			if phase3_admitted and not app.player.is_on_floor() and at.y>622 and air_shots==0:request_shot(Vector2(-signf(mount_goal.x-at.x)*.75,1),"recover_from_actual_knockback")
			router.set_source_axis(&"keyboard_mouse",signf(mount_goal.x-at.x) if absf(mount_goal.x-at.x)>7 else 0)
			if app.player.is_on_floor():
				if absf(mount_goal.x-at.x)<175 and frame>jump_release+2:
					router.set_jump_held(&"keyboard_mouse",false);router.set_jump_held(&"keyboard_mouse",true);jump_release=frame+25;event("mount_jump")
				else:router.set_jump_held(&"keyboard_mouse",false)
			elif frame>=jump_release:router.set_jump_held(&"keyboard_mouse",false)
		return
	mount_goal=Vector2.INF
	var gap_now:=absf(boss.motor.global_position.x-at.x)
	if heal_until>=frame and app.controller.actor_resources.health.current<app.controller.actor_resources.health.capacity and gap_now>220 and state not in ["seeds","seeds_warning","gust","gust_warning","lunge_warning"] and not app.focus_heal.blocked:
		router.set_source_axis(&"keyboard_mouse",0);router.set_jump_held(&"keyboard_mouse",false);router.set_focus_heal_held(&"keyboard_mouse",app.player.velocity.length()<10 and app.player.recoil_burst_remaining<=0);return
	heal_until=-1;router.set_focus_heal_held(&"keyboard_mouse",false)
	if app.focus_heal.available() and gap_now>260 and state in ["recover","turn","observe"] :
		heal_until=frame+95;event("heal_hold",{"hp":app.controller.actor_resources.health.current,"energy":app.controller.combat_energy.current});router.set_source_axis(&"keyboard_mouse",0);router.set_jump_held(&"keyboard_mouse",false);router.set_focus_heal_held(&"keyboard_mouse",false);return
	router.set_jump_held(&"keyboard_mouse",false)
	var aim:=pilot._clear_body_aim(view,boss.rig_pose(),at,boss.motor.to_global(boss.core_offset())) as Vector2
	var gap:=boss.motor.global_position.x-at.x
	var centre:=slab.get_center().x-30 if slab.position.x>1000 else slab.get_center().x+30
	var axis:=signf(centre-at.x) if absf(centre-at.x)>9 else 0.0
	if absf(gap)<180:axis=-signf(gap)
	router.set_source_axis(&"keyboard_mouse",axis)
	if frame-last_ground_shot>=15 and absf(gap)>165 and pilot._shot_clear(view,at,aim) and ground_safe(aim-at):request_shot(aim-at,"phase3_ground_counter")
func floor_cost(axis: float,jump: bool,horizon: float=.8) -> float:
	var at:=app.player.position
	var vy:=float(app.player.normal_velocity.y)
	var hold:=app.controller.jump_ability._hold_remaining
	if jump:vy=float(app.player.tuning.jump_speeds[0]);hold=app.player.tuning.jump_hold_duration
	var cost:=0.0
	for n: int in range(1,17):
		var dt:=horizon/16
		var t:=n*dt
		at.x=clampf(at.x+axis*260*dt,1325,1421)
		if hold>0:vy=float(app.player.tuning.jump_speeds[0]);hold-=dt
		else:vy=minf(800,vy+app.player.tuning.gravity*dt)
		at.y=minf(742,at.y+vy*dt)
		if at.y>=742:vy=0
		for projectile: Variant in boss._projectiles:
			if not is_instance_valid(projectile) or projectile.spent:continue
			var future: Vector2=projectile.global_position+projectile.direction*projectile.speed*t
			var gap:=Vector2(absf(future.x-at.x),absf(future.y-at.y))
			if gap.x<27 and gap.y<32:cost+=1000*(1.2-t)
	return cost
func floor_step() -> void:
	var at:=app.player.position
	var router:=app.controller.router
	var grounded:=app.player.is_on_floor()
	var best:=INF
	var chosen:=0.0
	var want_jump:=false
	for axis: float in [-1.0,0.0,1.0]:
		for jumping: bool in [false,true]:
			if jumping and (not grounded or frame<jump_release+3):continue
			var cost:=floor_cost(axis,jumping)+absf(clampf(at.x+axis*100,1325,1421)-1390)*.03+(2 if jumping else 0)
			if cost<best:best=cost;chosen=axis;want_jump=jumping
	if at.x>=1421 and chosen>0:chosen=0
	if at.x<=1325 and chosen<0:chosen=0
	var healing_safe:=grounded and app.focus_heal.available() and floor_cost(0,false,maxf(.15,1.15-app.focus_heal.elapsed))<.1
	if healing_safe and (heal_until>=frame or str(boss.mode) in ["stomp_warning","recover","phase_transition"]):
		if heal_until<frame:heal_until=frame+100;event("heal_hold",{"hp":app.controller.actor_resources.health.current,"energy":app.controller.combat_energy.current})
		router.set_source_axis(&"keyboard_mouse",0);router.set_jump_held(&"keyboard_mouse",false)
		router.set_focus_heal_held(&"keyboard_mouse",app.player.velocity.length()<10 and app.player.recoil_burst_remaining<=0)
		return
	heal_until=-1;router.set_focus_heal_held(&"keyboard_mouse",false)
	router.set_source_axis(&"keyboard_mouse",chosen)
	if want_jump:jump_release=frame+10;event("floor_dodge_jump")
	router.set_jump_held(&"keyboard_mouse",want_jump or (not grounded and frame<jump_release))
	if grounded and not want_jump and frame>jump_release and str(boss.mode)!="intro":
		var aim:=pilot._clear_body_aim(view,boss.rig_pose(),at,boss.motor.to_global(boss.core_offset())) as Vector2
		if floor_cost(1,false,.2)<.1 and pilot._shot_clear(view,at,aim):request_shot(aim-at,"floor_ground_counter")
func observe() -> void:
	if not active:return
	if not is_instance_valid(app.player) or not is_instance_valid(boss) or app.controller==null:return
	frame+=1
	var p:=app.player
	if p.is_on_floor():air_shots=0
	if boss.stage_phase!=last_phase:last_phase=boss.stage_phase;event("phase",{"phase":last_phase,"boss_hp":boss.health.current})
	if str(boss.mode)!=last_state:last_state=str(boss.mode);event("boss_state",{"state":last_state,"phase":last_phase})
	rows.append({"frame":frame,"movie_frame":Engine.get_process_frames()-start_movie,"player":point(p.position),"velocity":point(p.velocity),"grounded":p.is_on_floor(),"jump_held":not app.controller.router._jump_sources.is_empty(),"move_axis":app.controller.router.axis,"heal_held":app.controller.router.focus_heal_held(),"hp":app.controller.actor_resources.health.current,"session":app.controller.session_id,"boss_hp":boss.health.current,"boss_capacity":boss.health.capacity,"boss":point(boss.motor.global_position),"phase":boss.stage_phase,"mode":str(boss.mode),"focus":app.controller.air_focus_ability.active,"time_scale":Engine.time_scale,"stamina":app.controller.air_focus_ability.stamina,"crossing":phase3_crossing,"battle_finished":app.room.battle_finished})
func finish() -> void:
	active=false
	if app.controller!=null:app.controller.router.clear("recording ended")
	var file:=FileAccess.open(output,FileAccess.WRITE)
	file.store_string(JSON.stringify({"schema":1,"source_pr":150,"room":"P-R14","frames":frame,"start_movie_frame":start_movie,"initial_hp":initial_hp,"initial_boss_hp":initial_boss_hp,"failure":failure,"victory_frame":victory,"rows":rows,"events":events,"shots":shots,"source_pilot_helpers":["_clear_body_aim","_shot_clear"],"source_pilot_sha256":FileAccess.get_sha256("res://tools/windkeeper_pressure_01/legal_input_pilot.gd"),"source_scene_sha256":FileAccess.get_sha256("res://game/world/regions/P/rooms/P-R14.tscn"),"selection_seed":boss.definition.selection_seed if is_instance_valid(boss) else -1,"invincible":app.review.invincible,"position_writes_in_recorded_fight":false,"scope":"Declared isolated room entry before full live Boss. Original HP/AI/physics/resources/audio. Source aiming/occlusion helpers; predictive floor inputs and walk-off/focused recoil phase3. Declared right-side initial local position before the live fight. No mid-fight position, resource, boss phase/HP writes. Automated inputs, not human gameplay."},"  "));file.close()
	await WorldAudioLifecycle.drain_world(app)
	for helper: Node in [view,stage_view]:helper.free()
	app.queue_free();await ticks(5)
	quit(0 if failure.is_empty() else 1)
func run() -> void:
	root.size=Vector2i(1280,720)
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
		if arg.begins_with("--budget="):budget=int(arg.trim_prefix("--budget="))
	app=preload("res://game/application/world/fixed_world.tscn").instantiate();app.save_path="user://video_rush_windkeeper.json";root.add_child(app)
	if not await app.review.begin("P-R14","","base",false):failure="review entry failed";quit(1);return
	await ticks(3)
	app.controller.router.clear("declared initial local Boss approach")
	app.player.reset_at(Vector2(1400,742))
	boss=app.room.encounter as WindkeeperPressureEncounter
	pilot=SOURCE_PILOT.new()
	view=AppView.new();view.player=app.player
	stage_view=StageView.new();stage_view.boss=app.room.boss;view.stage=stage_view
	app.controller.shoot_ability.shot_fired.connect(shot_fired)
	app.controller.segment_returned.connect(func() -> void:failure="actual hazard checkpoint return; preserve as failed attempt")
	initial_hp=app.controller.actor_resources.health.current;initial_session=app.controller.session_id;initial_boss_hp=boss.health.current
	start_movie=Engine.get_process_frames();active=true;physics_frame.connect(observe)
	var last_damage := 0
	var previous_hp := initial_boss_hp
	for i: int in budget:
		await physics_frame
		if not failure.is_empty():break
		if app.controller==null or not is_instance_valid(boss) or not is_instance_valid(app.player):failure="player or encounter released";break
		if app.controller.session_id!=initial_session or app.controller.actor_resources.health.current<=0 or app.room.room_id!="P-R14":failure="player died, room changed or session restarted";break
		if boss.health.terminal:
			victory=frame;event("victory",{"boss_hp":boss.health.current,"player_hp":app.controller.actor_resources.health.current});app.controller.router.clear("actual victory");await ticks(210);break
		if boss.health.current<previous_hp:last_damage=frame;previous_hp=boss.health.current
		if frame-last_damage>1800:failure="no Boss damage for30 seconds; preserve stalled input diagnostic";break
		if app.busy or not app.controller.active:
			if not pending.is_empty():event("aim_cancel",{"reason":"source-owned accepted-hit presentation paused control"});pending.clear()
			app.controller.router.set_aim(&"keyboard_mouse",Vector2.RIGHT,false)
			heal_until=-1
			continue
		if not pending.is_empty():focus_step()
		elif boss.stage_phase==3:phase3_step()
		else:
			floor_step()

		if frame%600==0:print("WINDKEEPER PROGRESS ",frame," hp=",app.controller.actor_resources.health.current," boss=",boss.health.current," phase=",boss.stage_phase," mode=",boss.mode," at=",app.player.position," boss_at=",boss.motor.global_position," focus=",app.controller.air_focus_ability.active," pending=",not pending.is_empty())
	if victory<0 and failure.is_empty():failure="bounded fight budget exhausted"
	if victory>=0 and last_phase!=3:failure="Boss defeated without the requested three-phase coverage; reject this take"
	if not failure.is_empty():event("failed",{"reason":failure,"boss_hp":boss.health.current if is_instance_valid(boss) else -1,"player_hp":app.controller.actor_resources.health.current if app.controller!=null else -1})
	await finish()
