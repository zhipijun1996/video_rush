extends "res://tests/mapgen_formal_route_runner.gd"
## Reuse source routes/go/bank and native scene. Select a less demanding real
## path through the same complete generated map; never remove modules/enemies.
var capture_output := "res://build/video_rush/mapgen.json"
var selected_steps: Array=[]
var route_complete := false
var full_boss_defeat := false
var action_events: Array=[]
var recorded_manifest: Dictionary={}
var recorded_map_hash := ""
var ready_frame := -1
var overview_frames: Array=[]
func overview() -> void:
	# Explicit camera-only, frozen-world survey, never represented as play.
	var camera: Camera2D=app._run_camera
	var old_zoom: Vector2=camera.zoom
	var old_position: Vector2=camera.global_position
	var bounds: Rect2=camera.world_bounds
	app.controller.router.clear("camera_only_frozen_world_overview")
	paused=true;camera.set_physics_process(false);camera.set_process(false)
	overview_frames.append(Engine.get_process_frames())
	for i: int in 1200:
		if i<300:
			camera.zoom=Vector2.ONE*minf(1280.0/bounds.size.x,720.0/bounds.size.y)*.9
			camera.global_position=bounds.get_center()
		else:
			var progress: float=float(i-300)/899.0
			camera.zoom=Vector2.ONE*.48
			camera.global_position=Vector2(lerpf(bounds.position.x+700,bounds.end.x-700,progress),bounds.get_center().y)
		camera.force_update_scroll();await process_frame
	overview_frames.append(Engine.get_process_frames())
	camera.zoom=old_zoom;camera.global_position=old_position;camera.set_physics_process(true);camera.force_update_scroll();paused=false
	await process_frame
func _initialize() -> void:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--seed="):route_seed=a.trim_prefix("--seed=")
		elif a.begins_with("--output="):capture_output=a.trim_prefix("--output=")
	run.call_deferred()
func routes(source: Dictionary) -> Array:
	var start: String=str(source.result.map.anchors.start_departure.instance_id)+"/"+str(source.result.map.anchors.start_departure.port_id)
	var goal: String=str(source.result.map.anchors.boss_arrival.instance_id)+"/"+str(source.result.map.anchors.boss_arrival.port_id)
	var graph: Dictionary={}
	for instance: Dictionary in source.result.map.instances:
		var name: String=str(instance.module_id).to_lower()
		var penalty := 0.0
		for token: String in ["climb","moving","lift","workshop","turret","ambush","carrier","timed","relay","vertical"]:
			if token in name:penalty+=50.0
		for route: Dictionary in instance.routes:
			var a: String=str(instance.id)+"/"+str(route.from_port)
			var b: String=str(instance.id)+"/"+str(route.to_port)
			if not graph.has(a):graph[a]=[]
			graph[a].append({"target":b,"instance":instance,"route":route,"cost":3.0+penalty})
	for link: Dictionary in source.result.map.connections:
		var a: String=str(link.a.instance_id)+"/"+str(link.a.port_id)
		var b: String=str(link.b.instance_id)+"/"+str(link.b.port_id)
		if not graph.has(a):graph[a]=[]
		if not graph.has(b):graph[b]=[]
		graph[a].append({"target":b,"edge":link,"cost":1.0});graph[b].append({"target":a,"edge":link,"cost":1.0})
	var queue: Array=[start];var distance: Dictionary={start:0.0};var previous: Dictionary={start:{}}
	while not queue.is_empty():
		queue.sort_custom(func(a:String,b:String)->bool:return distance[a]<distance[b])
		var at: String=queue.pop_front()
		if at==goal:break
		for step: Dictionary in graph.get(at,[]):
			var cost: float=distance[at]+float(step.cost)
			if distance.has(step.target) and distance[step.target]<=cost:continue
			distance[step.target]=cost;var row: Dictionary=step.duplicate();row["from"]=at;previous[step.target]=row
			if not queue.has(step.target):queue.append(step.target)
	if not previous.has(goal):return []
	var result: Array=[];var at:=goal
	while at!=start:
		var row: Dictionary=previous[at];result.push_front(row);at=row.from
	return result
func frames(n:int) -> void:
	for i: int in n:
		# A normal defensive shot/jump when a live enemy is on this player's
		# current line; no enemy removal, health changes or resource grants.
		if is_instance_valid(app) and is_instance_valid(app.player) and app.lifetime.active:
			for enemy: EnemyMotor in app.stage.enemies:
				var actor: EnemyActor=enemy.get_node("Actor")
				if actor.health.terminal:continue
				var offset: Vector2=enemy.global_position-app.player.global_position
				if absf(offset.y)>120 or absf(offset.x)>220:continue
				if app.player.is_on_floor() and absf(offset.x)<130:app.controller.router.request_action(&"jump")
				if app.controller.shoot_ability.cooldown_remaining<=0 and app.controller.action_resources.shot_charges>0:
					var ray:=PhysicsRayQueryParameters2D.create(app.player.global_position,enemy.global_position,1,[app.player.get_rid()])
					if app.player.get_world_2d().direct_space_state.intersect_ray(ray).is_empty():
						var queued: bool=app.controller.router.request_action(&"shoot_release",offset.normalized())
						action_events.append({"tick":ticks,"kind":"normal_enemy_aim","queued":queued,"direction":[offset.normalized().x,offset.normalized().y]})
				break
		await super.frames(1)
func run() -> void:
	root.size=Vector2i(1280,720);root.content_scale_size=Vector2i(1280,720)
	app=load(ProjectSettings.get_setting("application/run/main_scene")).instantiate();app.meta_persistence_enabled=false;root.add_child(app)
	for i: int in 3:await process_frame
	app.menu._start_title_adventure();await frames(2);app.start_plains(route_seed)
	if not await READY.ready(app,self):failures+=1;await finish();return
	ready_frame=Engine.get_process_frames()
	recorded_manifest=app.stage.generated.manifest.duplicate(true)
	recorded_map_hash=app.stage.level_plan.map_hash
	var source: Dictionary=preload("res://addons/mapgen/data_json.gd").parse(app.stage.generated.manifest.mapgen.source_json).value
	await overview()
	selected_steps=routes(source)
	print("VIDEO RUSH MAPGEN PATH ",selected_steps.map(func(s:Dictionary)->String:return str(s.instance.module_id) if s.has("instance") else "connection"))
	if selected_steps.is_empty():failures+=1;await finish();return
	var ok:=true
	for step: Dictionary in selected_steps:
		if not app.lifetime.active:ok=false;break
		if step.has("route"):
			var origin:=Vector2(step.instance.origin_blocks[0],step.instance.origin_blocks[1])*128.0
			if step.route.has("author_path_pixels"):
				for point: Array in step.route.author_path_pixels.slice(1,-1):
					if not await go(origin+Vector2(point[0],point[1]),900,true):ok=false;break
			if ok and not await go(bank(str(step.instance.id),str(step.route.to_port)),900,false):ok=false
		else:
			var parts: PackedStringArray=str(step.target).split("/")
			if not await go(bank(parts[0],parts[1]),240,false):ok=false
		if not ok:break
	route_complete=ok and app.lifetime.active
	if route_complete:
		app.controller.router.clear("weighted_route_to_boss")
		var boss: Node=app.stage.boss.get_node("Encounter")
		var pilot: RefCounted=load("res://tools/bellstrider_01/legal_input_pilot.gd").new()
		for i: int in 10800:
			if not app.lifetime.active or app.controller.actor_resources.health.terminal:break
			if boss.health.terminal:full_boss_defeat=true;await frames(180);break
			pilot.step(app,boss,boss.combat_metrics(),[])
			await frames(1)
	if not route_complete:failures+=1
	await finish()
func finish() -> void:
	var data: Dictionary={"seed":route_seed,"input_only":true,"ready_process_frame":ready_frame,"overview_process_frames":overview_frames,"overview_scope":"Frozen original generated scene; camera-only survey, explicitly not gameplay","route_complete":route_complete,"boss_defeated":full_boss_defeat,"failures":failures,"trace":trace,"recording_input_events":action_events,"selected_steps":selected_steps,"manifest":recorded_manifest,"actual_map_hash":recorded_map_hash,"scope":"Weighted choice among existing generated routes; complete106-module source pool unchanged; input-only actor, not a human playability proof"}
	if is_instance_valid(app.stage):data.actual_map_hash=app.stage.level_plan.map_hash;data.manifest=app.stage.generated.manifest.duplicate(true)
	DirAccess.make_dir_recursive_absolute(capture_output.get_base_dir());FileAccess.open(capture_output,FileAccess.WRITE).store_string(JSON.stringify(data))
	if app.lifetime.active:app.abandon_run()
	for i: int in 8:await process_frame
	await preload("res://tests/audio_teardown.gd").drain_world(app);app.queue_free()
	for i: int in 3:await process_frame
	print("VIDEO RUSH MAPGEN complete=",route_complete," boss=",full_boss_defeat," failures=",failures)
	quit(0 if failures==0 else 1)
