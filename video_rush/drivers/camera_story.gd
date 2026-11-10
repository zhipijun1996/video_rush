extends "res://tests/world/plains_intro.gd"
## Frozen PR147 source helpers; original controller inputs after declared local starts.
var clock_frames := 0
var segments: Array = []
var rows: Array = []
var active_label := ""
var active_start := 0
func observe() -> void:
	clock_frames += 1
	if active_label != "" and is_instance_valid(app) and is_instance_valid(app.room):
		var camera := app.camera as WorldCamera
		var center := camera.get_screen_center_position()
		var width := camera.get_viewport_rect().size.x/camera.zoom.x
		var conceal := false
		if app.room.camera_concealers.has("secret"):conceal=app.room.camera_concealers.secret.visible
		rows.append({"clip":active_label,"relative_frame":clock_frames-active_start,"position":[app.player.position.x,app.player.position.y],"camera":[center.x,center.y],"zoom":camera.zoom.x,"room":app.room.room_id,"lead":camera.lead,"observation_direction":camera.observation_direction,"actor_screen_fraction_x":(app.player.position.x-center.x+width/2)/width,"zone":camera.zones.active_id,"transition":not camera.zones.transition.is_empty(),"concealed":conceal,"chest_open":app.state.value.receipts.has("open_P24_hidden_chest"),"session_id":app.controller.session_id,"health":app.controller.actor_resources.health.current})
	if clock_frames>7200:
		failures+=1;active_label="";finish_capture.call_deferred()
func mark(id: String) -> void:
	active_label=id;active_start=clock_frames
func end() -> void:
	segments.append({"id":active_label,"start_frame":active_start,"end_frame":clock_frames});active_label=""
func setup(rid: String,point: Vector2) -> void:
	active_label=""
	check(await app.review.begin(rid,"","base"),"declared local review "+rid)
	app.controller.router.clear("local camera recording start");app.player.reset_at(point)
	await ticks(3);(app.camera as WorldCamera).reset_view();await ticks(80)
func key(code: Key,held: bool) -> void:
	var e:=InputEventKey.new();e.physical_keycode=code;e.pressed=held
	app.player.get_node("KeyboardMouseAdapter")._unhandled_input(e)
func walk_x(goal: float) -> void:
	for i: int in 240:
		var delta:=goal-app.player.position.x
		if absf(delta)<7:
			app.controller.router.set_source_axis(&"keyboard_mouse",0);return
		app.controller.router.set_source_axis(&"keyboard_mouse",signf(delta));await ticks(1)
	app.controller.router.clear("walk limit");check(false,"bounded horizontal walk "+str(goal))
func load_candidate(rid: String,point: Vector2) -> void:
	active_label=""
	# Exact source bridge copied from PR147 tests/world/plains_next_batch.gd.
	var source:=load("res://game/world/regions/P/rooms/"+rid+".tscn").instantiate() as FixedWorldRoom
	var draft:=WorldRoomDraft.extract(source);check(WorldRoomDraft.validate(source,draft).is_empty(),"candidate codec "+rid);source.free()
	draft.base_content_version=app.content.workbench_base_version();draft.revision=1
	var catalog: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(FixedWorldProvider.WORKBENCH_CATALOG))
	var row: Dictionary=catalog.rooms[rid]
	draft.geometry={"bounds":row.world_geometry.bounds_world_units,"space_rects":row.world_geometry.space_rects,"doors":row.doors}
	await app.workbench._handle({"channel":"gunman-workbench","type":"load_draft","request_id":rid,"revision":1,"draft":draft,"stage":"base","paused":false})
	await ticks(4);check(app.room.room_id==rid,"source candidate loaded "+rid)
	app.controller.router.clear("candidate local start");app.player.reset_at(point);await ticks(3);(app.camera as WorldCamera).reset_view();await ticks(50)
func run() -> void:
	root.size=Vector2i(1280,720);physics_frame.connect(observe)
	app=preload("res://game/application/world/fixed_world.tscn").instantiate();app.save_path="user://video_rush_camera_story.json";root.add_child(app);app.workbench.enabled=true
	await setup("P-R01",Vector2(1050,1262));mark("lead")
	app.controller.router.set_source_axis(&"keyboard_mouse",1);await ticks(35)
	app.controller.router.set_source_axis(&"keyboard_mouse",0);await ticks(50)
	app.controller.router.set_aim(&"keyboard_mouse",Vector2.LEFT,true);await ticks(30)
	app.controller.router.request_action(&"shoot_release",Vector2.LEFT);app.controller.router.set_aim(&"keyboard_mouse",Vector2.LEFT,false);await ticks(45)
	app.controller.router.set_source_axis(&"keyboard_mouse",-1);await ticks(55)
	app.controller.router.set_source_axis(&"keyboard_mouse",0);await ticks(80);end()
	await setup("P-R01",Vector2(1050,1262));mark("jump")
	await ticks(35);app.controller.router.set_jump_held(&"keyboard_mouse",true);await ticks(14);app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(90)
	app.controller.router.set_jump_held(&"keyboard_mouse",true);await ticks(45);app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(100);end()
	await setup("P-R22",Vector2(800,1486));mark("recoil")
	check(await cross(Vector2(1168,1390),Vector2(-1,.6)),"real first recoil")
	check(await walk(Vector2(1824,1390),"P-R22"),"middle bank")
	check(await cross(Vector2(2224,1326),Vector2(-1,.45)),"real second recoil");await ticks(30);end()
	await setup("P-R22",Vector2(832,142));mark("fall")
	check(await path([Vector2(880,334),Vector2(736,526),Vector2(416,782),Vector2(544,1038),Vector2(256,1262),Vector2(544,1486)],"P-R22"),"continuous descent");await ticks(20);end()
	await setup("P-R01",Vector2(1050,1262));mark("look")
	key(KEY_W,true);await ticks(85);key(KEY_W,false);await ticks(65);key(KEY_S,true);await ticks(85);key(KEY_S,false);await ticks(40)
	key(KEY_W,true);await ticks(40);app.controller.router.request_action(&"jump");await ticks(35);key(KEY_W,false);await ticks(50);end()
	await setup("P-R23",Vector2(1584,526));mark("corner")
	# Exact current tutorial input from PR147 tests/world/plains_intro.gd.
	app.controller.router.set_jump_held(&"keyboard_mouse",true);await ticks(11)
	app.controller.router.request_action(&"shoot_release",Vector2(.6,.8))
	var landed:=false
	for i: int in 90:
		await ticks(1)
		if app.player.is_on_floor() and app.player.position.y<340:landed=true;break
	app.controller.router.clear("upper platform landing");check(landed,"authored recoil climb");await ticks(140);end()
	# One continuous local sequence; no reset or state/position write between markers.
	await setup("P-R24",Vector2(1136,1102));check(app.room.camera_concealers.secret.visible,"concealed from main passage");mark("secret_preview")
	key(KEY_W,true);await ticks(65);key(KEY_W,false);await ticks(35);key(KEY_S,true);await ticks(65);key(KEY_S,false);await ticks(35)
	check(app.room.camera_concealers.secret.visible,"manual look cannot expose chamber");end()
	mark("secret_enter")
	await walk_x(1040);await ticks(25);await walk_x(1136);await ticks(25)
	await walk_x(676);await ticks(40)
	check(not app.room.camera_concealers.secret.visible and (app.camera as WorldCamera).zones.active_id=="secret","real plant entry selects hidden composition")
	app._interact();await ticks(90);check(app.state.value.receipts.has("open_P24_hidden_chest"),"actual nearby chest interaction committed");end()
	mark("secret_return")
	await walk_x(1136);await ticks(55);key(KEY_W,true);await ticks(50);key(KEY_W,false);await ticks(25)
	check(app.room.camera_concealers.secret.visible and (app.camera as WorldCamera).zones.active_id!="secret","return restores main composition and concealment")
	check(app.state.value.receipts.has("open_P24_hidden_chest"),"reward remains opened on return");end()
	await load_candidate("P-R14",Vector2(440,742));mark("arena")
	app.controller.router.set_source_axis(&"keyboard_mouse",1);await ticks(55);app.controller.router.set_source_axis(&"keyboard_mouse",0);await ticks(165)
	check(app.room.battle_started,"actual Boss entry activated");check((app.camera as WorldCamera).zones.active_id=="arena","arena composition active");end()
	await finish_capture()
func finish_capture() -> void:
	if physics_frame.is_connected(observe):physics_frame.disconnect(observe)
	var output:="user://trace.json"
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
	var f:=FileAccess.open(output,FileAccess.WRITE)
	f.store_string(JSON.stringify({"frames":clock_frames,"failures":failures,"segments":segments,"rows":rows,"scope":"PR147 draft scene local-start recordings using original controller and real collisions. P14 via exact source workbench bridge; not continuous main progression/full clear/device FPS. Hidden preview/entry/return are one uninterrupted input sequence, actual chest interaction, no flag or position writes.","position_writes_within_marked_clips":false},"  "));f.close()
	await WorldAudioLifecycle.drain_world(app);app.queue_free();await ticks(5);quit(failures)
