extends SceneTree
## Film fixture only: original formal App, one initial equipment selection,
## existing Router -> Controller -> Motor. No physics/art/gameplay modifications.
var app: DemoApp
var rows: Array[Dictionary] = []
var events: Array[Dictionary] = []
var demo := "gun_up"
var frames := 480
var output := "res://build/video_rush/trace.json"
var failures: Array[String] = []
var accepted := 0
var start_position := Vector2.ZERO
var seed := "level-design-v2-baseline/08"
func _initialize() -> void: run.call_deferred()
func tick() -> void:
	await physics_frame
	await RenderingServer.frame_post_draw
func run() -> void:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--case="):demo=arg.trim_prefix("--case=")
		if arg.begins_with("--frames="):frames=int(arg.trim_prefix("--frames="))
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
	root.size=Vector2i(1280,720)
	app=preload("res://scenes/demo/demo.tscn").instantiate() as DemoApp
	app.meta_persistence_enabled=false
	root.add_child(app)
	for i: int in 8: await tick()
	if not app.start_plains(seed): failures.append("start_plains rejected")
	for i: int in 180:
		if app.stage is PlainsRegionStage and app.stage.is_node_ready() and app.stage.assembly_ok and not app._stage_pending:break
		await tick()
	if not app.stage is PlainsRegionStage:
		printerr("SHOWCASE FAIL: formal stage missing");quit(1);return
	var c:=app.controller
	var weapon := "pulse_gun"
	if demo.begins_with("shuriken"):weapon="shadow_shuriken"
	if demo=="fan_turn":weapon="fan_shuriken"
	if demo.begins_with("laser"):weapon="sustained_laser"
	if demo=="triple_up":weapon="triple_machine_gun"
	if not c.shoot_ability.equip(load("res://resources/weapons/"+weapon+".tres")):failures.append("equip rejected")
	# Like the game's committed normal-speed action driver, disable optional aim
	# slow-time for a readable real-time movement demonstration; no tuning edits.
	c.air_focus_ability.enabled=false
	c.router.activate_device(&"gamepad")
	c.shoot_ability.shot_fired.connect(func(direction: Vector2,id: int):
		accepted+=1;events.append({"kind":"accepted_shot","frame":rows.size(),"id":id,"direction":[direction.x,direction.y]}))
	c.shoot_ability.behavior().phase_changed.connect(func(value: StringName):
		if demo.begins_with("laser") and value==&"beam":
			accepted+=1;events.append({"kind":"accepted_beam","frame":rows.size()}))
	for i: int in 20:await tick()
	start_position=app.player.global_position
	for f: int in frames:
		var g:=f%240
		await physics_frame
		c.router.activate_device(&"gamepad")
		c.router.set_move_axis(0)
		var aim:=Vector2.DOWN
		if demo in ["gun_side","shuriken_side","fan_turn"]:aim=Vector2.LEFT
		if demo=="fan_turn" and g>=51:aim=Vector2.RIGHT
		if demo in ["gun_side","shuriken_side"] and f>=240:aim=Vector2.RIGHT
		var held:=demo.begins_with("laser") and g>=35 and g<(50 if demo=="laser_stop" else 100)
		c.router.set_aim(&"gamepad",aim,held)
		if g==20:c.router.request_action(&"jump")
		if g==32:c.router.request_action(&"jump_release")
		if g==35 and demo!="jump_control" and not demo.begins_with("laser"):c.router.request_action(&"shoot_release",aim)
		if demo in ["gun_two","gun_empty"] and g==55:c.router.request_action(&"shoot_release",aim)
		if demo=="gun_empty" and g in [75,95,115]:c.router.request_action(&"shoot_release",aim)
		if demo=="gun_recover" and f==260:
			c.router.request_action(&"jump")
		if demo=="gun_recover" and f==275:c.router.request_action(&"shoot_release",aim)
		if demo=="gun_recover" and f==280:c.router.request_action(&"jump_release")
		await RenderingServer.frame_post_draw
		var runtime:=c.shoot_ability.behavior()
		rows.append({"frame":f,"position":[app.player.global_position.x,app.player.global_position.y],"velocity":[app.player.velocity.x,app.player.velocity.y],"grounded":app.player.is_on_floor(),"phase":str(runtime.phase),"hp":c.actor_resources.health.current,"stamina":c.actor_resources.stamina.current,"shots":c.action_resources.shot_charges,"epoch":app.lifetime.epoch,"actor_epoch":app.lifetime.actor_epoch,"weapon":str(c.shoot_ability.weapon.id),"accepted_shots":accepted})
	c.router.clear("video_capture_end")
	if rows.size()!=frames:failures.append("incomplete trace")
	if demo=="jump_control" and accepted!=0:failures.append("control unexpectedly fired")
	if demo!="jump_control" and accepted<1:failures.append("no accepted attack")
	if rows.any(func(row:Dictionary)->bool:return row.hp<=0):failures.append("player died")
	if rows.any(func(row:Dictionary)->bool:return row.epoch!=rows[0].epoch or row.actor_epoch!=rows[0].actor_epoch):failures.append("respawn/session change")
	var receipt={"kind":"video_rush_formal_weapon_demo","case":demo,"weapon":weapon,"seed":seed,"manifest_hash":app.stage.generated.manifest.manifest_hash,"frames":rows,"events":events,"failures":failures,"accepted_shots":accepted,"initial_position":[start_position.x,start_position.y],"initialization":"Formal App start at default spawn; equipment selected through existing equip API; optional aim slow-time disabled; original input Router and Motor","no_midflight_position_health_resource_injection":true,"scope":"Developer equipment demonstration, not natural unlocks, whole-route completion or physical-device performance"}
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output.get_base_dir()))
	var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(receipt));file.close()
	app.free();await process_frame
	print("VIDEO RUSH SHOWCASE: ",demo," ",rows.size()," frames, ",accepted," attacks, ",failures.size()," failures")
	quit(0 if failures.is_empty() else 1)
