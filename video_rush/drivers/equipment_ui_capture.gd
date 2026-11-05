extends "res://tests/run_gear_formal_movie.gd"
## Original formal UI/input route. Observation adapts the old stat-only
## assertion to N01's actual production time-scale resolver. No game edits.
func frames(count: int) -> void:
	var hold := 190 if count in [90,100] else count
	for i: int in hold:
		await super.frames(1)
		if rows.is_empty() or not is_instance_valid(app) or not is_instance_valid(app.controller): continue
		rows[-1].effects=[]
		for source: Dictionary in app.build.effect_sources():
			rows[-1].effects.append({"instance_id":str(source.instance_id),"definition_id":str(source.definition_id),"parameters":source.parameters})
		var resolver: Callable=app.controller.air_focus_ability.world_scale_resolver
		if resolver.is_valid():
			rows[-1].resolved_focus_scale=resolver.call(app.controller.motor.tuning.focus_time_scale)
			rows[-1].base_focus_scale=app.controller.motor.tuning.focus_time_scale

func set_phase(value: String) -> void:
	super.set_phase(value)
	caption.text=value.replace("属性效果生效","装备状态生效")+"\n宝箱站位为演示设置；领取、装备和卸下使用原生操作"

func check(value: bool, message: String) -> bool:
	if message=="actual formal controller stat changes from the equipped cache definition":
		var owned: RunItemInstance=app.build.inventory.instances()[0]
		if owned.definition_id==&"N01":
			var expected: float=owned.item.parameters_for_level(owned.level).world_slow_scale
			var resolver: Callable=app.controller.air_focus_ability.world_scale_resolver
			var actual: float=resolver.call(app.controller.motor.tuning.focus_time_scale) if resolver.is_valid() else -1.0
			return super.check(is_equal_approx(actual,expected) and not app.build.effect_sources().is_empty(),"N01 equips through native UI and its actual production resolver selects the catalog world-slow scale")
	if message=="native unequip removes the actual controller effect while retaining ownership":
		var resolver: Callable=app.controller.air_focus_ability.world_scale_resolver
		var baseline: float=app.controller.motor.tuning.focus_time_scale
		value=value and app.build.effect_sources().is_empty() and resolver.is_valid() and is_equal_approx(resolver.call(baseline),baseline)
	return super.check(value,message)
