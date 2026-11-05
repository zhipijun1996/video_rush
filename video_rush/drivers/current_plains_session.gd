extends SceneTree
## Full source-owned live traversal policy -> source-owned legal-input Boss pilot.
## Map2 is a disclosed independent level entry. No player positioning or HP writes.
const TRACE = preload("res://tests/level_formal_trace.gd")
var app: DemoApp
var route_driver: RefCounted
var pilot: RefCounted
var output := "res://build/video_rush/plains.json"
var seed_value := "level-design-v2-baseline"
var map_index := 1
var route_policy := "kill_from_bank_v2"
var pilot_mode := "cautious2"
var charge_jump := "original"
var attack_pressure := false
var route_report: Dictionary = {}
var rows: Array = []
var events: Array = []
var failures: Array = []
var phase := "initializing"
var encounter: Node
var start_frame := 0
var actual_boss_start := -1
var actual_boss_end := -1
var live := false
func _initialize() -> void:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="): output=arg.trim_prefix("--output=")
		elif arg.begins_with("--seed="): seed_value=arg.trim_prefix("--seed=")
		elif arg.begins_with("--map="): map_index=int(arg.trim_prefix("--map="))
		elif arg.begins_with("--policy="): route_policy=arg.trim_prefix("--policy=")
		elif arg.begins_with("--pilot="): pilot_mode=arg.trim_prefix("--pilot=")
		elif arg.begins_with("--charge-jump="): charge_jump=arg.trim_prefix("--charge-jump=")
		elif arg=="--attack-pressure": attack_pressure=true
	run.call_deferred()
func frame() -> void:
	await process_frame
func sample() -> void:
	if not live or not is_instance_valid(app.player) or not is_instance_valid(app.controller): return
	var r := {"process_frame":Engine.get_process_frames(),"physics_frame":Engine.get_physics_frames(),"phase":phase,"position":[app.player.global_position.x,app.player.global_position.y],"velocity":[app.player.velocity.x,app.player.velocity.y],"hp":app.controller.actor_resources.health.current,"air_shots":app.controller.action_resources.shot_charges,"actor_epoch":app.lifetime.actor_epoch,"stage_epoch":app.lifetime.stage_epoch,"axis":app.controller.router.axis}
	if is_instance_valid(encounter): r.boss_hp=encounter.health.current;r.boss_state=str(encounter.mode);r.boss_active=app._boss_started
	rows.append(r)
func units() -> Array[Dictionary]:
	var values: Array[Dictionary]=[]
	for p: Dictionary in app.stage.pickups:
		if p.get("kind","")=="coin" and ("boss" in str(p.get("source","")) or "bellstrider" in str(p.get("source","")) or "windkeeper" in str(p.get("source",""))): values.append(p.duplicate(true))
	return values
func run() -> void:
	root.size=Vector2i(1280,720);root.content_scale_size=Vector2i(1280,720)
	app=DemoApp.new();app.meta_persistence_enabled=false;root.add_child(app)
	if not app.start_plains(seed_value): failures.append("formal_start_refused");await finish();return
	for i: int in 240:
		await frame()
		if app.stage is PlainsRegionStage and not app._stage_pending: break
	if not app.stage is PlainsRegionStage: failures.append("main_plain_not_ready");await finish();return
	if map_index==2:
		app.lifetime.stage_epoch+=1;app.lifetime.actor_epoch+=1
		app.director.region_map_index=2;app.director._enter_stage(2,&"boss");app._stage_entered(DemoRunResult.new())
		for i: int in 240:
			await frame()
			if app.stage is PlainsRegionStage and not app._stage_pending and app.stage.map_index==2: break
	if not app.stage is PlainsRegionStage or app.stage.map_index!=map_index: failures.append("wrong_map");await finish();return
	encounter=app.stage.boss.get_node("Encounter")
	start_frame=Engine.get_process_frames();live=true;process_frame.connect(sample)
	route_driver=TRACE.new()
	if not route_driver.attach(app,"fast",0,route_policy): failures.append("route_attach_refused");await finish();return
	route_driver.frame_budget=18000
	route_driver.visible_input_post_draw=DisplayServer.get_name()!="headless"
	route_driver.observe_input_timing=route_driver.visible_input_post_draw
	phase="route"
	if route_driver.visible_input_post_draw: await RenderingServer.frame_post_draw
	route_driver.run_route.call_deferred()
	while not route_driver.finished and not route_driver.terminated: await frame()
	route_report={"outcome":route_driver.outcome,"frames":route_driver.observed_frames,"edges":route_driver.observed_edges,"events":route_driver.events,"initial":route_driver.initial_runtime,"final":route_driver.final_runtime}
	route_driver.seal_test_observation();route_driver.disconnect_test_observers()
	if route_driver.outcome!="route_target_reached" or not app.lifetime.active: failures.append("route_incomplete/"+route_driver.outcome);await finish();return
	# Release the traversal policy's held inputs before the next input policy
	# takes over. This does not move, heal or reconfigure the actor.
	app.controller.router.clear("route_to_boss_input_handoff")
	app.controller.router.activate_device(&"keyboard_mouse")
	pilot=load("res://tools/bellstrider_01/legal_input_pilot.gd" if map_index==1 else "res://tools/windkeeper_pressure_01/legal_input_pilot.gd").new()
	pilot.mode=pilot_mode;phase="boss"
	if pilot.has_method("observe_actual_shot"): app.controller.shoot_ability.shot_fired.connect(func(_d:Vector2,id:int):pilot.observe_actual_shot(id))
	var death_frame := -1
	for i: int in 18000:
		if not app.lifetime.active or not is_instance_valid(app.player) or app.controller.actor_resources.health.terminal: failures.append("player_died");break
		if app._boss_started and actual_boss_start<0: actual_boss_start=Engine.get_process_frames()
		if encounter.health.terminal:
			if death_frame<0: death_frame=Engine.get_process_frames();actual_boss_end=death_frame;phase="boss_defeated"
			if Engine.get_process_frames()-death_frame>=240: break
		if map_index==1 and charge_jump=="on_roll" and encounter.mode in [&"roll_warning",&"combo_warning"]:
			# Recording-bot decision only: wait for real roll movement before
			# asking for its normal jump; do not start a jump during the warning.
			var dx: float=app.stage.boss.global_position.x-app.player.global_position.x
			app.controller.router.set_jump_held(&"keyboard_mouse",false)
			app.controller.router.set_source_axis(&"keyboard_mouse",signf(dx) if absf(dx)>200 else 0.0)
		else:
			pilot.step(app,encounter,encounter.combat_metrics(),units())
		if map_index==2 and attack_pressure and app._boss_started and not encounter.health.terminal and (app.player.is_on_floor() or (encounter.health.current<=8 and app.controller.action_resources.shot_charges>0)) and app.controller.shoot_ability.cooldown_remaining<=0 and app.player.recoil_burst_remaining<=0:
			# Ordinary extra shots in real clear grounded windows. The game
			# still owns cooldown, recoil, energy, collision, damage and death.
			var at: Vector2=app.player.global_position
			var aim: Vector2=pilot._clear_body_aim(app,encounter.rig_pose(),at,app.stage.boss.to_global(encounter.core_offset()))
			var direction: Vector2=(aim-at).normalized()
			var back: Vector2=at-direction*95
			var floor_ray:=PhysicsRayQueryParameters2D.create(back+Vector2(0,17),back+Vector2(0,52),1,[app.player.get_rid()])
			var safe: bool=(not app.player.is_on_floor() and encounter.health.current<=8) or not app.player.get_world_2d().direct_space_state.intersect_ray(floor_ray).is_empty()
			if safe and pilot._shot_clear(app,at,aim) and absf(app.stage.boss.global_position.x-at.x)>140:
				var queued: bool=app.controller.router.request_action(&"shoot_release",direction)
				events.append({"process_frame":Engine.get_process_frames(),"action":"shoot_release","aim":[direction.x,direction.y],"queued":queued,"purpose":"normal extra shot in real clear grounded opportunity"})
		if map_index==1 and charge_jump=="on_roll" and encounter.mode==&"roll" and not app.player.is_on_floor() and app.player.velocity.y < -50 and app.player.velocity.y > -600 and app.controller.action_resources.shot_charges>0 and app.controller.shoot_ability.cooldown_remaining<=0:
			var distance: float=absf(app.stage.boss.global_position.x-app.player.global_position.x)
			if distance<300:
				var accepted: bool=app.controller.router.request_action(&"shoot_release",Vector2.DOWN)
				events.append({"process_frame":Engine.get_process_frames(),"action":"shoot_release","aim":[0,1],"queued":accepted,"purpose":"normal recoil-jump clearance of actual charging Boss"})
		await frame()
	if is_instance_valid(encounter) and not encounter.health.terminal: failures.append("boss_not_defeated")
	await finish()
func finish() -> void:
	live=false
	if process_frame.is_connected(sample):process_frame.disconnect(sample)
	var data := {"scope":"independent_complete_plain_route_then_original_Boss_pilot","seed":seed_value,"map":map_index,"entry":"normal main plain1" if map_index==1 else "explicit independent main plain2; no false map1 defeat or reward","rows":rows,"route":route_report,"failures":failures,"boss_start_process_frame":actual_boss_start,"boss_defeat_process_frame":actual_boss_end,"initial_recorded_process_frame":start_frame,"no_midrun_position_health_resource_injection":true,"automated_player":true,"route_policy":route_policy,"pilot_mode":pilot_mode,"charge_jump_policy":charge_jump,"attack_pressure":attack_pressure}
	if is_instance_valid(encounter):data.boss_metrics=encounter.combat_metrics()
	data.recording_input_events=events
	if pilot!=null:data.pilot_inputs=pilot.input_rows
	if is_instance_valid(app.stage):data.manifest=app.stage.generated.manifest.duplicate(true)
	DirAccess.make_dir_recursive_absolute(output.get_base_dir());FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify(data))
	if is_instance_valid(app):
		if is_instance_valid(app.controller):app.controller.router.clear("recording_end")
		await preload("res://tests/audio_teardown.gd").drain_world(app)
		app.free()
	await process_frame;await process_frame
	print("VIDEO RUSH PLAIN ",map_index," failures=",failures," boss_defeat=",actual_boss_end)
	quit(0 if failures.is_empty() else 1)
