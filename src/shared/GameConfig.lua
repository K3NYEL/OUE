--!strict
-- Valores base migrados desde game/config.py.
-- Mantener esta tabla como fuente única de balance.

local GameConfig = {
	ArenaSize = 40,
	RadarRange = 30,
	IntermissionSeconds = 20,
	MaxEnemiesAlive = 20,
	MaxWaveEnemies = 40,

	Player = {
		MaxHealth = 100,
		WalkSpeed = 16,
		SprintSpeed = 24,
		MaxStamina = 100,
	},

	EnemyTypes = {
		normal = { Health = 40, Speed = 3.6, Damage = 10, Points = 10, Size = Vector3.new(1, 1.8, 1), Ranged = false },
		rapido = { Health = 22, Speed = 6.8, Damage = 7, Points = 15, Size = Vector3.new(0.8, 1.4, 0.8), Ranged = false },
		tanque = { Health = 170, Speed = 2.1, Damage = 24, Points = 40, Size = Vector3.new(1.8, 2.6, 1.8), Ranged = false },
		tirador = { Health = 35, Speed = 3, Damage = 12, Points = 25, Size = Vector3.new(1, 1.8, 1), Ranged = true },
		jefe = { Health = 900, Speed = 2.6, Damage = 35, Points = 300, Size = Vector3.new(3.2, 4.5, 3.2), Ranged = false },
	},

	Abilities = {
		dash = { Key = Enum.KeyCode.Q, Cooldown = 5 },
		onda = { Key = Enum.KeyCode.E, Cooldown = 14 },
		torreta = { Key = Enum.KeyCode.F, Cooldown = 18 },
		furia = { Key = Enum.KeyCode.C, Cooldown = 45 },
	},
}

return table.freeze(GameConfig)
