--!strict
local GameConfig = {
	ArenaSize = 40,
	RadarRange = 30,
	IntermissionSeconds = 20,
	MaxEnemiesAlive = 20,
	MaxWaveEnemies = 40,
	Player = { MaxHealth = 100, WalkSpeed = 16, SprintSpeed = 24, MaxStamina = 100 },
	EnemyTypes = {
		normal = { Health = 40, Speed = 3.6, Damage = 10, Points = 10, Size = Vector3.new(1, 1.8, 1), Color = Color3.fromRGB(220, 55, 65), Ranged = false, Shoots = false },
		rapido = { Health = 22, Speed = 6.8, Damage = 7, Points = 15, Size = Vector3.new(.8, 1.4, .8), Color = Color3.fromRGB(255, 145, 45), Ranged = false, Shoots = false },
		tanque = { Health = 170, Speed = 2.1, Damage = 24, Points = 40, Size = Vector3.new(1.8, 2.6, 1.8), Color = Color3.fromRGB(150, 90, 210), Ranged = false, Shoots = false },
		tirador = { Health = 35, Speed = 3, Damage = 12, Points = 25, Size = Vector3.new(1, 1.8, 1), Color = Color3.fromRGB(55, 180, 255), Ranged = true, Shoots = true },
		jefe = { Health = 900, Speed = 2.6, Damage = 35, Points = 300, Size = Vector3.new(3.2, 4.5, 3.2), Color = Color3.fromRGB(220, 40, 180), Ranged = false, Shoots = true },
	},
	Weapons = {
		{ Name="Pistola", Damage=28, FireRate=.28, Magazine=12, Reserve=48, MaxReserve=120, Reload=1, Pellets=1, Spread=.004, Automatic=false, Kick=.8, Explosion=0, Penetration=1, Price=0, Color=Color3.fromRGB(75,75,82), Size=Vector3.new(.1,.14,.5), Description="Precisa y fiable. Buena para empezar." },
		{ Name="Rifle", Damage=14, FireRate=.09, Magazine=30, Reserve=90, MaxReserve=240, Reload=1.6, Pellets=1, Spread=.018, Automatic=true, Kick=.5, Explosion=0, Penetration=1, Price=0, Color=Color3.fromRGB(130,130,135), Size=Vector3.new(.1,.13,.8), Description="Fuego automatico a gran cadencia." },
		{ Name="Escopeta", Damage=11, FireRate=.85, Magazine=6, Reserve=18, MaxReserve=48, Reload=2, Pellets=8, Spread=.07, Automatic=false, Kick=3, Explosion=0, Penetration=1, Price=0, Color=Color3.fromRGB(110,75,55), Size=Vector3.new(.14,.14,.75), Description="8 perdigones. Devastadora a corta distancia." },
		{ Name="Francotirador", Damage=120, FireRate=1.3, Magazine=5, Reserve=15, MaxReserve=40, Reload=2.2, Pellets=1, Spread=0, Automatic=false, Kick=4, Explosion=0, Penetration=3, Price=600, Color=Color3.fromRGB(65,85,110), Size=Vector3.new(.08,.12,1.1), Description="Atraviesa hasta 3 enemigos. Clic derecho = zoom." },
		{ Name="Lanzagranadas", Damage=90, FireRate=1, Magazine=4, Reserve=8, MaxReserve=24, Reload=2.4, Pellets=1, Spread=.005, Automatic=false, Kick=3.5, Explosion=6, Penetration=1, Price=900, Color=Color3.fromRGB(85,105,50), Size=Vector3.new(.16,.16,.6), Description="Explosion en area (radio 6). Ideal contra hordas." },
	},
	WeaponUpgrades = {
		{ Key="Damage", Name="Dano", Cost=120, Description="+25% de dano por nivel." },
		{ Key="Magazine", Name="Cargador", Cost=80, Description="+25% de cargador y municion maxima." },
		{ Key="FireRate", Name="Cadencia", Cost=100, Description="Dispara 10% mas rapido por nivel." },
		{ Key="Reload", Name="Recarga", Cost=80, Description="Recarga 15% mas rapida por nivel." },
	},
	Perks = {
		{ Key="Health", Name="Vida maxima", Cost=150, Max=5, Description="+20 de vida maxima por nivel." },
		{ Key="Speed", Name="Velocidad", Cost=150, Max=4, Description="+8% de velocidad por nivel." },
		{ Key="Fire", Name="Municion incendiaria", Cost=300, Max=3, Description="Tus ataques aplican quemadura." },
		{ Key="Vampire", Name="Robo de vida", Cost=250, Max=3, Description="Recuperas vida por baja." },
		{ Key="Drone", Name="Dron de combate", Cost=350, Max=3, Description="Un dron adicional te ayuda." },
	},
	Abilities = {
		dash = { Key="Q", Cooldown=5, Max=3 },
		onda = { Key="E", Cooldown=14, Max=3 },
		torreta = { Key="F", Cooldown=18, Max=4 },
		furia = { Key="C", Cooldown=45, Max=3 },
	},
	Supplies = {
		{ Key="Heal", Name="Curacion completa", Cost=100, Description="Restaura toda tu vida." },
		{ Key="Ammo", Name="Municion completa", Cost=150, Description="Rellena todas las armas." },
	},
}
return table.freeze(GameConfig)
