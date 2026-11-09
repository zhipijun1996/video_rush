extends SceneTree
## New game to station, real input only. No position, health, ability or progress writes.
var app: FixedWorldApp
var failures:=0
var require_preview:=false
var replay_save_path:="user://plains_intro_replay.json"
func _initialize() -> void:run.call_deferred()
func ticks(n: int) -> void:
	for i: int in n:await physics_frame
func settle() -> void:
	for i: int in 240:
		await physics_frame
		if not app.busy:return
func check(ok: bool,label: String) -> void:
	print("INTRO ",ok," ",label)
	if not ok:failures+=1
func visible_before_action(point: Vector2,label: String) -> void:
	if not require_preview:return
	var half:=app.camera.get_viewport_rect().size/(2*app.camera.zoom)
	var view:=Rect2(app.camera.get_screen_center_position()-half,half*2).grow(-8)
	var visible_point:=point+Vector2(0,18)
	for door: Dictionary in app.room.doors:
		var portal:=FixedWorldProvider.point(door.position_candidate.local_world_units)
		if door.direction in ["up","down"] and portal.distance_to(visible_point)<40:
			var edge:=app.camera.get_screen_center_position().y+half.y*(1 if door.direction=="down" else -1)
			check(absf(edge-portal.y)<2,"continuous approach sees edge-aligned doorway "+label);return
	check(view.has_point(visible_point),"continuous approach sees "+label+" "+str(point))

func walk(point: Vector2,rid: String) -> bool:
	var held:=0
	var preview_checked:=false
	for i: int in 700:
		await physics_frame
		if app.busy:continue
		if app.room.room_id!=rid:print("WALK TRANSITION ",rid," -> ",app.room.room_id," at ",app.player.position);return true
		var at:=app.player.position
		if i%120==0:print("WALK ",rid," ",at," -> ",point," hp=",app.controller.actor_resources.health.current)
		if absf(at.x-point.x)<8 and absf(at.y-point.y)<12 and app.player.is_on_floor():
			app.controller.router.clear("waypoint");return true
		var dx:=point.x-at.x
		if require_preview and not preview_checked and app.player.is_on_floor() and point.y>at.y+100:
			var ahead:=at+Vector2(signf(dx)*32,0)
			var ray:=PhysicsRayQueryParameters2D.create(ahead,ahead+Vector2(0,24),1)
			if app.player.get_world_2d().direct_space_state.intersect_ray(ray).is_empty():
				visible_before_action(point,rid+" next descent at last safe edge");preview_checked=true
		app.controller.router.set_source_axis(&"keyboard_mouse",signf(dx) if absf(dx)>3 else 0)
		if point.y>at.y+40 and absf(dx)<30 and app.player.is_on_floor():app.controller.router.request_action(&"drop_through")
		if app.player.is_on_floor() and point.y<at.y-30 and absf(dx)<300:
			if not preview_checked:visible_before_action(point,rid+" next ascent");preview_checked=true
			app.controller.router.set_jump_held(&"keyboard_mouse",false);app.controller.router.set_jump_held(&"keyboard_mouse",true);held=32
		elif held>0:
			held-=1
			if held==0:app.controller.router.set_jump_held(&"keyboard_mouse",false)
	printerr("STUCK ",rid," ",app.player.position," -> ",point," ",app.status);return false
func path(points: Array,rid: String) -> bool:
	for p: Vector2 in points:
		if not await walk(p,rid):return false
	return true
func recoil_jump(direction: Vector2) -> void:
	app.controller.router.set_source_axis(&"keyboard_mouse",1)
	app.controller.router.set_jump_held(&"keyboard_mouse",true)
	await ticks(9);app.controller.router.request_action(&"shoot_release",direction)
	await ticks(7);app.controller.router.set_jump_held(&"keyboard_mouse",false)
	for i: int in 100:
		await physics_frame
		if app.player.is_on_floor():break
	app.controller.router.clear("landing")
	print("RECOIL LAND ",app.player.position)
func cross(at: Vector2,aim: Vector2=Vector2.ZERO,shot_frame: int=9) -> bool:
	visible_before_action(at,app.room.room_id+" next jump landing")
	app.controller.router.clear("approach")
	app.controller.router.set_source_axis(&"keyboard_mouse",signf(at.x-app.player.position.x))
	app.controller.router.set_jump_held(&"keyboard_mouse",true)
	for i: int in 160:
		await physics_frame
		if i==shot_frame and aim!=Vector2.ZERO:app.controller.router.request_action(&"shoot_release",aim.normalized())
		var dx:=at.x-app.player.position.x
		app.controller.router.set_source_axis(&"keyboard_mouse",signf(dx) if absf(dx)>4 else 0)
		if i==32:app.controller.router.set_jump_held(&"keyboard_mouse",false)
		if i>8 and app.player.is_on_floor():break
	app.controller.router.clear("cross_landed")
	print("CROSS ",app.room.room_id," ",app.player.position," -> ",at)
	if absf(app.player.position.y-at.y)>8:return false
	return await walk(at,app.room.room_id)
func ride(name: String,origin: Vector2,leave_y: float,destination: Vector2) -> bool:
	var lift:=app.room.get_node(name) as WorldMovingPlatform
	app.controller.router.clear("wait_for_cage")
	var previous:=lift.position.distance_to(origin)
	for i: int in 1800:
		await physics_frame
		if not is_instance_valid(lift):return false
		var current:=lift.position.distance_to(origin)
		if current<1 or (current<160 and current<previous):break
		previous=current
	app.controller.router.set_jump_held(&"keyboard_mouse",true)
	var boarded:=false
	for i: int in 180:
		await physics_frame
		if not is_instance_valid(lift):return false
		var dx:=lift.position.x-app.player.position.x
		app.controller.router.set_source_axis(&"keyboard_mouse",signf(dx) if absf(dx)>4 else 0)
		if i==32:app.controller.router.set_jump_held(&"keyboard_mouse",false)
		if i>8 and app.player.is_on_floor() and absf(app.player.position.y-lift.position.y+28)<8:boarded=true;break
	app.controller.router.clear("boarded")
	if not boarded:printerr("BOARD FAILED ",name," ",app.player.position," ",lift.position);return false
	for i: int in 1800:
		await physics_frame
		if not is_instance_valid(lift):return false
		if i%60==0:print("RIDE ",name," rider=",app.player.position," lift=",lift.position," floor=",app.player.is_on_floor())
		if lift.position.y<leave_y:break
	return await cross(destination)
func station_hall() -> bool:
	return await ride("StationLift",Vector2(544,1744),1344,Vector2(1328,1262))

## Camera comparison adapter. Movement helpers above are frozen from
## gunman-rush@29bd6b58cfe80d38f6ef5a8d3b843b59115f8af8/tests/world/plains_intro.gd.
## Explicit fixture starts only; no player/health/progress writes within marked clips.
var clock_frames := 0
var segments: Array = []
var rows: Array = []
var active_label := ""
var active_start := 0
func observe() -> void:
	clock_frames += 1
	if active_label != "" and is_instance_valid(app) and is_instance_valid(app.room) and is_instance_valid(app.player):
		var center := app.camera.get_screen_center_position()
		rows.append({"clip":active_label,"relative_frame":clock_frames-active_start,"position":[app.player.position.x,app.player.position.y],"velocity":[app.player.velocity.x,app.player.velocity.y],"camera":[center.x,center.y],"zoom":app.camera.zoom.x,"room":app.room.room_id,"grounded":app.player.is_on_floor()})
	if clock_frames > 7200:
		active_label="";failures+=1;finish_capture.call_deferred()
func begin_clip(id: String) -> void:
	active_label=id;active_start=clock_frames
func end_clip() -> void:
	segments.append({"id":active_label,"start_frame":active_start,"end_frame":clock_frames});active_label=""
func setup(rid: String,point: Vector2) -> void:
	active_label=""
	check(await app.review.begin(rid,"","base"),"review fixture "+rid)
	app.controller.router.clear("camera_fixture")
	app.player.reset_at(point)
	await ticks(3)
	if app.camera.has_method("reset_view"):app.camera.call("reset_view")
	else:app.camera.call("enter_room",FixedWorldProvider.rect(app.room.contract.world_geometry.bounds_world_units))
	await ticks(80)
func key(code: Key,held: bool) -> void:
	var e:=InputEventKey.new();e.physical_keycode=code;e.pressed=held
	app.player.get_node("KeyboardMouseAdapter")._unhandled_input(e)
func run() -> void:
	root.size=Vector2i(1280,720)
	physics_frame.connect(observe)
	require_preview=false
	app=preload("res://game/application/world/fixed_world.tscn").instantiate();app.save_path="user://video_rush_camera_compare.json";root.add_child(app)
	await setup("P-R23",Vector2(600,622));begin_clip("turn")
	app.controller.router.set_source_axis(&"keyboard_mouse",1);await ticks(28)
	app.controller.router.set_source_axis(&"keyboard_mouse",0);await ticks(40)
	app.controller.router.set_aim(&"keyboard_mouse",Vector2.LEFT,true);await ticks(25)
	app.controller.router.request_action(&"shoot_release",Vector2.LEFT)
	app.controller.router.set_aim(&"keyboard_mouse",Vector2.LEFT,false);await ticks(45)
	app.controller.router.set_source_axis(&"keyboard_mouse",-1);await ticks(38)
	app.controller.router.set_source_axis(&"keyboard_mouse",0);await ticks(65);end_clip()
	await setup("P-R23",Vector2(800,622));begin_clip("jump")
	await ticks(35);app.controller.router.set_jump_held(&"keyboard_mouse",true);await ticks(14);app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(90)
	app.controller.router.set_jump_held(&"keyboard_mouse",true);await ticks(45);app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(100);end_clip()
	await setup("P-R22",Vector2(800,1486));begin_clip("recoil")
	check(await cross(Vector2(1168,1390),Vector2(-1,.6)),"first real recoil")
	check(await walk(Vector2(1824,1390),"P-R22"),"same middle bank")
	check(await cross(Vector2(2224,1326),Vector2(-1,.45)),"second real recoil");await ticks(30);end_clip()
	await setup("P-R22",Vector2(832,142));begin_clip("fall")
	check(await path([Vector2(880,334),Vector2(736,526),Vector2(416,782),Vector2(544,1038),Vector2(256,1262),Vector2(544,1486)],"P-R22"),"real canal descent");await ticks(20);end_clip()
	await setup("P-R23",Vector2(800,622));begin_clip("look")
	key(KEY_W,true);await ticks(85);key(KEY_W,false);await ticks(65)
	key(KEY_S,true);await ticks(85);key(KEY_S,false);await ticks(40)
	key(KEY_W,true);await ticks(40);app.controller.router.request_action(&"jump");await ticks(35);key(KEY_W,false);await ticks(50);end_clip()
	await setup("P-R23",Vector2(1056,526));begin_clip("corner")
	check(await path([Vector2(1190,430),Vector2(1380,334),Vector2(1232,238),Vector2(1088,142),Vector2(1088,-18)],"P-R23"),"same shelter corner");await settle();await ticks(30);end_clip()
	await finish_capture()
func finish_capture() -> void:
	if physics_frame.is_connected(observe):physics_frame.disconnect(observe)
	var output:="user://trace.json"
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
	var f:=FileAccess.open(output,FileAccess.WRITE)
	f.store_string(JSON.stringify({"frames":clock_frames,"failures":failures,"segments":segments,"rows":rows,"scope":"Six declared local starts; original controller inputs and collision. No natural progression/full clear, human playtest or device FPS claim.","position_writes_within_marked_clips":false},"  "));f.close()
	await WorldAudioLifecycle.drain_world(app);app.queue_free();await ticks(5);quit(failures)
