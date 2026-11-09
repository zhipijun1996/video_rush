extends "res://tests/world/plains_intro.gd"
## Source-owned route helpers, original controller. No position/health/progress writes.
var clock_frames := 0
var markers: Array = []
var observations: Array = []
var previous_room := ""
func observe() -> void:
	clock_frames += 1
	if app != null and app.room != null:
		if app.room.room_id != previous_room:
			previous_room = app.room.room_id
			markers.append({"event":"room_enter","room":previous_room,"frame":clock_frames})
		if clock_frames % 6 == 0:
			observations.append({"frame":clock_frames,"room":previous_room,"position":[app.player.position.x,app.player.position.y],"hp":app.controller.actor_resources.health.current})
	if clock_frames > 3600:
		failures += 1
		finish_recording.call_deferred()
func run() -> void:
	root.size = Vector2i(1280,720)
	physics_frame.connect(observe)
	require_preview = true
	app = preload("res://game/application/world/fixed_world.tscn").instantiate()
	app.save_path = "user://video_rush_intro.json"
	root.add_child(app)
	check(app.start_new(),"normal new game")
	await settle()
	if app.room == null:
		failures += 1
		await finish_recording()
		return
	markers.append({"event":"route_start","frame":clock_frames})
	check(await path([Vector2(600,1774),Vector2(880,1710),Vector2(992,1710)],"P-R03"),"source meadow approach")
	check(await cross(Vector2(1232,1646)),"source first jump")
	check(await walk(Vector2(1632,1646),"P-R03"),"source second approach")
	check(await cross(Vector2(1888,1582)),"source second jump")
	check(await walk(Vector2(2310,1582),"P-R03"),"actual room boundary crossing")
	await settle()
	check(app.room.room_id == "P-R21","arrived through actual doorway")
	markers.append({"event":"map_open","frame":clock_frames})
	app._pause_world()
	app.ui.show_map()
	await ticks(240)
	markers.append({"event":"map_close","frame":clock_frames})
	app._close_panel()
	if failures == 0:
		check(await path([Vector2(352,526),Vector2(736,526),Vector2(848,686),Vector2(1008,846)],"P-R21"),"source carriage descent")
		for i: int in 180:
			await physics_frame
			if i % 24 == 0:
				for enemy: EnemyActor in app.room.enemies.values():
					if not enemy.health.terminal:
						app.controller.router.request_action(&"shoot_release",(enemy.motor.position-app.player.position).normalized())
						break
		check(await walk(Vector2(1264,782),"P-R21"),"upper firing angle")
		for i: int in 100:
			await physics_frame
			if i % 24 == 0:
				var enemy: EnemyActor = app.room.enemies["P-R21:encounter:02"]
				if not enemy.health.terminal:app.controller.router.request_action(&"shoot_release",(enemy.motor.position-app.player.position).normalized())
		check(await path([Vector2(1264,782),Vector2(1440,942),Vector2(1600,1134)],"P-R21"),"actual lower exit")
		await settle()
		check(app.room.room_id == "P-R22","canal entry")
		if failures == 0:
			check(await path([Vector2(912,334),Vector2(736,526),Vector2(416,782),Vector2(544,1038),Vector2(256,1262),Vector2(544,1486),Vector2(800,1486)],"P-R22"),"source canal approach")
			markers.append({"event":"recoil_start","frame":clock_frames})
			check(await cross(Vector2(1168,1390),Vector2(-1,.6)),"actual first canal recoil landing")
			markers.append({"event":"recoil_end","frame":clock_frames})
			await ticks(60)
	await finish_recording()
func finish_recording() -> void:
	physics_frame.disconnect(observe)
	var output := "user://trace.json"
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="): output = arg.trim_prefix("--output=")
	var data := {"source_route":"tests/world/plains_intro.gd","frames":clock_frames,"failures":failures,"markers":markers,"rows":observations,"scope":"New-game route excerpt through grass slope/carriage/canal, actual crossings, explored map, shooting and first recoil landing. Not a full-region clear or human playtest.","player_position_health_progress_writes":false}
	var f := FileAccess.open(output,FileAccess.WRITE)
	f.store_string(JSON.stringify(data,"  ")); f.close()
	await WorldAudioLifecycle.drain_world(app)
	app.queue_free()
	await ticks(5)
	quit(failures)
