--!strict
-- Datos de armas trasladados desde game/config.py.
-- Los assets de audio se asignarán mediante IDs publicados en Roblox.

local WeaponConfig = {
	{
		Name = "Pistola", Damage = 28, FireRate = 0.28, Magazine = 12,
		InitialReserve = 48, MaxReserve = 120, ReloadTime = 1,
		Pellets = 1, Spread = 0.004, Automatic = false, Kick = 0.8,
		ExplosionRadius = 0, Penetration = 1, Price = 0,
	},
	{
		Name = "Rifle", Damage = 14, FireRate = 0.09, Magazine = 30,
		InitialReserve = 90, MaxReserve = 240, ReloadTime = 1.6,
		Pellets = 1, Spread = 0.018, Automatic = true, Kick = 0.5,
		ExplosionRadius = 0, Penetration = 1, Price = 0,
	},
	{
		Name = "Escopeta", Damage = 11, FireRate = 0.85, Magazine = 6,
		InitialReserve = 18, MaxReserve = 48, ReloadTime = 2,
		Pellets = 8, Spread = 0.07, Automatic = false, Kick = 3,
		ExplosionRadius = 0, Penetration = 1, Price = 0,
	},
	{
		Name = "Francotirador", Damage = 120, FireRate = 1.3, Magazine = 5,
		InitialReserve = 15, MaxReserve = 40, ReloadTime = 2.2,
		Pellets = 1, Spread = 0, Automatic = false, Kick = 4,
		ExplosionRadius = 0, Penetration = 3, Price = 600,
	},
	{
		Name = "Lanzagranadas", Damage = 90, FireRate = 1, Magazine = 4,
		InitialReserve = 8, MaxReserve = 24, ReloadTime = 2.4,
		Pellets = 1, Spread = 0.005, Automatic = false, Kick = 3.5,
		ExplosionRadius = 6, Penetration = 1, Price = 900,
	},
}

return table.freeze(WeaponConfig)
