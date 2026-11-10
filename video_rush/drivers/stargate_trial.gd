extends SceneTree
## Isolated hwdq preset once at entry; all subsequent motion is original input.
var app: FixedWorldApp
var frame := 0
var phase := "load"
var rows: Array = []
var events: Array = []
var inputs: Array = []
var capabilities: Dictionary = {}
var failures := 0
var output := "user://stargate-trace.json"
var finished := false
var returned := false
func _initialize() -> void: run.call_deferred()
func observe() -> void:
	frame+=1
	if is_instance_valid(app) and is_instance_valid(app.player) and phase!="load":
		rows.append({"frame":frame,"phase":phase,"p":[app.player.position.x,app.player.position.y],"v":[app.player.velocity.x,app.player.velocity.y],"state":str(app.controller.traversal.state),"floor":app.player.is_on_floor(),"session":app.controller.session_id,"hp":app.controller.actor_resources.health.current,"q_cooldown":app.q_guard.cooldown,"shots":app.controller.action_resources.shot_charges,"latch":app.state.has("starbridge_v12_return_open")})
func ticks(n: int) -> void:
	for i: int in n: await physics_frame
func mark(label: String) -> void:
	phase=label;events.append({"phase":label,"frame":frame});print("TRIAL ",frame," ",label," ",app.player.position," ",app.controller.traversal.state)
func axis(x: float) -> void: app.controller.router.set_source_axis(&"keyboard_mouse",x)
func shoot(aim: Vector2) -> void:
	inputs.append({"frame":frame,"action":"shoot_release","aim":[aim.x,aim.y]})
	app.controller.router.request_action(&"shoot_release",aim.normalized())
func jump() -> void:
	inputs.append({"frame":frame,"action":"jump_edge"})
	app.controller.router.set_jump_held(&"keyboard_mouse",false);await ticks(1)
	app.controller.router.set_jump_held(&"keyboard_mouse",true)
func hook(point: Vector2) -> void:
	inputs.append({"frame":frame,"action":"grapple","target":[point.x,point.y]})
	app.controller.router.request_action(&"grapple",(point-app.player.position-Vector2(0,-6)).normalized())
func wait_wall(minx: float,maxx: float,budget: int=60) -> bool:
	for i: int in budget:
		await ticks(1)
		if app.controller.traversal.state==&"wall_attach" and app.player.position.x>=minx and app.player.position.x<=maxx:return true
	return false
func wait_hook() -> bool:
	for i: int in 70:
		await ticks(1)
		if app.controller.traversal.state==&"hook_hang":return true
	return false
func require(ok: bool,label: String) -> bool:
	if not ok:failures+=1;mark("incomplete_"+label)
	return ok
func end() -> void:
	axis(0);await ticks(60)
	physics_frame.disconnect(observe)
	var f:=FileAccess.open(output,FileAccess.WRITE)
	f.store_string(JSON.stringify({"schema":1,"room":"V-R12","frames":frame,"rows":rows,"events":events,"inputs":inputs,"capabilities":capabilities,"failures":failures,"finish_latch":finished,"returned_to_entry":returned,"position_writes_after_entry":false,"scope":"Computer-operated isolated hwdq workbench trial. Original controller/physics/hazards/audio. Not normal progression, human play, or fun acceptance."},"  "));f.close()
	await WorldAudioLifecycle.drain_world(app);app.queue_free();await ticks(5);quit(failures)
func run() -> void:
	root.size=Vector2i(1280,720);physics_frame.connect(observe)
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
	app=preload("res://game/application/world/fixed_world.tscn").instantiate()
	app.save_path="user://video_rush_stargate_trial.json";root.add_child(app);app.workbench.enabled=true
	var source:=preload("res://game/world/regions/V/rooms/V-R12.tscn").instantiate() as FixedWorldRoom
	var draft:=WorldRoomDraft.extract(source);source.free()
	draft.base_content_version=app.content.workbench_base_version();draft.revision=1
	var catalog: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(FixedWorldProvider.WORKBENCH_CATALOG))
	var row: Dictionary=catalog.rooms["V-R12"]
	draft.geometry={"bounds":row.world_geometry.bounds_world_units,"space_rects":row.world_geometry.space_rects,"doors":row.doors}
	await app.workbench._handle({"channel":"gunman-workbench","type":"load_draft","request_id":"video_rush_trial","revision":1,"draft":draft,"stage":"hwdq","paused":false})
	if not require(app.workbench.last_event.get("type")=="draft_loaded","load"):await end();return
	capabilities={"H":app.controller.traversal.hook_enabled,"W":app.controller.traversal.wall_enabled,"D":app.controller.traversal.double_enabled,"Q":app.q_guard.owned}
	if not require(app.player.is_on_floor() and not capabilities.values().has(false),"entry_preset"):await end();return
	mark("entry");await ticks(90)
	mark("entry_to_w1");axis(1);await jump();await ticks(8);shoot(Vector2(-.8,.6));await ticks(10);await jump()
	if not require(await wait_wall(300,360,45),"w1"):await end();return
	mark("w1_to_h1")
	for i: int in 360:
		if app.player.position.y>=1798:break
		await ticks(1)
	shoot(Vector2.LEFT);await ticks(12);axis(0);await jump();await ticks(2);hook(Vector2(544,1648))
	if not require(await wait_hook(),"h1"):await end();return
	mark("h1_to_w3")
	while app.q_guard.cooldown>0:await ticks(1)
	shoot(Vector2.DOWN);await ticks(10);axis(1);await jump()
	if not require(await wait_wall(560,620,45),"w3"):await end();return
	mark("w3_to_relay")
	await jump();await ticks(1);axis(-1);await ticks(5);shoot(Vector2.DOWN);await ticks(10);axis(1);await jump()
	var relay:=false
	for i: int in 120:
		await ticks(1)
		if app.player.position.x>710:axis(0)
		if app.player.is_on_floor() and app.player.position.y<1250 and app.player.position.x>624:relay=true;break
	if not require(relay,"relay"):await end();return
	mark("relay");axis(0);await ticks(45)
	mark("relay_to_w4");axis(1);await jump();await ticks(8);shoot(Vector2(-.8,.6));await ticks(10);await jump()
	if not require(await wait_wall(870,920,60),"w4"):await end();return
	mark("w4_to_h2");await jump();await ticks(2);shoot(Vector2.RIGHT);axis(-1)
	for i: int in 60:
		await ticks(1)
		if app.player.position.x<685:break
	axis(0);await jump();await ticks(10);hook(Vector2(624,704))
	if not require(await wait_hook(),"h2"):await end();return
	mark("h2_to_w5")
	while app.q_guard.cooldown>0:await ticks(1)
	shoot(Vector2(.94,-.34));axis(-1);await ticks(12);await jump()
	var inner:=false
	for i: int in 100:
		await ticks(1)
		if app.player.position.x<425 and app.player.position.y<785:axis(0)
		elif app.player.position.y>=785:axis(-1)
		if app.controller.traversal.state==&"wall_attach" and app.player.position.x<440:inner=true;break
	if not require(inner,"w5"):await end();return
	mark("w5_to_w6");await jump();await ticks(1);axis(1);await ticks(7);shoot(Vector2(-.8,.6));await ticks(10);await jump()
	if not require(await wait_wall(630,680,70),"w6"):await end();return
	mark("w6_to_finish");await jump();await ticks(1);axis(-1);await ticks(5);shoot(Vector2.DOWN);await ticks(10);axis(1);await jump()
	var top:=false
	for i: int in 140:
		await ticks(1)
		if app.player.position.x>860:axis(0)
		if app.player.is_on_floor() and app.player.position.y<330 and app.player.position.x>784:top=true;break
	if not require(top,"finish_platform"):await end();return
	mark("finish_platform");axis(1)
	for i: int in 40:
		await ticks(1)
		if app.player.position.x>860:break
	axis(0);app._interact();await ticks(40)
	finished=app.state.has("starbridge_v12_return_open")
	if not require(finished,"latch"):await end();return
	mark("return_bridge");axis(-1)
	for i: int in 240:
		await ticks(1)
		if app.player.position.x<122:break
	axis(0);app.controller.router.request_action(&"drop_through");await ticks(12)
	mark("return_chute")
	for i: int in 240:
		await ticks(1)
		if app.player.is_on_floor() and app.player.position.y>1800:returned=true;break
	require(returned,"return_entry");mark("returned" if returned else "stopped");await end()
