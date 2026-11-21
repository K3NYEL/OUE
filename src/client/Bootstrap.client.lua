--!strict
-- HUD y controles del cliente. La autoridad del juego permanece en el servidor.
local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local UIS=game:GetService("UserInputService")
local RunService=game:GetService("RunService")
local player=Players.LocalPlayer
local remotes=ReplicatedStorage:WaitForChild("OUE_Remotes")
local Action=remotes:WaitForChild("Action") :: RemoteEvent
local State=remotes:WaitForChild("State") :: RemoteEvent
local Notice=remotes:WaitForChild("Notice") :: RemoteEvent
local Config=require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameConfig"))
local current:any={}
local shopOpen=false
local paused=false
local firing=false
local sprinting=false
local gui=Instance.new("ScreenGui"); gui.Name="OUE_HUD"; gui.ResetOnSpawn=false; gui.IgnoreGuiInset=true; gui.Parent=player:WaitForChild("PlayerGui")
local function makeLabel(parent:Instance,name:string,text:string,size:number,pos:UDim2,anchor:Vector2?):TextLabel
 local l=Instance.new("TextLabel"); l.Name=name; l.BackgroundTransparency=1; l.Text=text; l.TextColor3=Color3.fromRGB(240,246,252); l.Font=Enum.Font.GothamBold; l.TextSize=size; l.TextXAlignment=Enum.TextXAlignment.Left; l.Position=pos; l.AnchorPoint=anchor or Vector2.zero; l.Size=UDim2.fromOffset(420,28); l.Parent=parent; return l
end
local function makePanel(name:string,pos:UDim2,size:UDim2):Frame
 local f=Instance.new("Frame"); f.Name=name; f.Position=pos; f.Size=size; f.BackgroundColor3=Color3.fromRGB(13,17,23); f.BackgroundTransparency=.1; f.BorderSizePixel=0; f.Parent=gui
 local c=Instance.new("UICorner"); c.CornerRadius=UDim.new(0,8); c.Parent=f
 local s=Instance.new("UIStroke"); s.Color=Color3.fromRGB(215,38,61); s.Transparency=.25; s.Parent=f
 return f
end
local hud=makePanel("HUD",UDim2.fromOffset(16,16),UDim2.fromOffset(330,138))
local stats=makeLabel(hud,"Stats","Puntos: 0 | Creditos: $0",14,UDim2.fromOffset(12,8))
local wave=makeLabel(hud,"Wave","OLEADA 0",18,UDim2.fromOffset(12,36))
local health=makeLabel(hud,"Health","Vida: 100 / 100",14,UDim2.fromOffset(12,66))
local healthBack=Instance.new("Frame"); healthBack.Position=UDim2.fromOffset(12,100); healthBack.Size=UDim2.fromOffset(300,12); healthBack.BackgroundColor3=Color3.fromRGB(55,55,60); healthBack.BorderSizePixel=0; healthBack.Parent=hud
local healthFill=Instance.new("Frame"); healthFill.Size=UDim2.fromScale(1,1); healthFill.BackgroundColor3=Color3.fromRGB(215,38,61); healthFill.BorderSizePixel=0; healthFill.Parent=healthBack
local radar=Instance.new("Frame"); radar.Name="Radar"; radar.Size=UDim2.fromOffset(124,124); radar.Position=UDim2.new(1,-18,0,18); radar.AnchorPoint=Vector2.new(1,0); radar.BackgroundColor3=Color3.fromRGB(10,15,20); radar.BackgroundTransparency=.18; radar.Parent=gui
local radarCorner=Instance.new("UICorner"); radarCorner.CornerRadius=UDim.new(1,0); radarCorner.Parent=radar
local radarStroke=Instance.new("UIStroke"); radarStroke.Color=Color3.fromRGB(215,38,61); radarStroke.Transparency=.2; radarStroke.Parent=radar
local radarCenter=Instance.new("Frame"); radarCenter.Size=UDim2.fromOffset(6,6); radarCenter.Position=UDim2.fromScale(.5,.5); radarCenter.AnchorPoint=Vector2.new(.5,.5); radarCenter.BackgroundColor3=Color3.new(1,1,1); radarCenter.BorderSizePixel=0; radarCenter.Parent=radar
local radarDots:{Frame}={}
local function updateRadar(positions:{Vector3})
 local root=player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
 local cam=workspace.CurrentCamera
 if not root or not cam then return end
 for i,pos in ipairs(positions) do
  local dot=radarDots[i]
  if not dot then dot=Instance.new("Frame"); dot.Name="EnemyDot"; dot.Size=UDim2.fromOffset(5,5); dot.BackgroundColor3=Color3.fromRGB(255,65,75); dot.BorderSizePixel=0; dot.Parent=radar; local corner=Instance.new("UICorner"); corner.CornerRadius=UDim.new(1,0); corner.Parent=dot; radarDots[i]=dot end
  local delta=pos-root.Position
  local forward=cam.CFrame.LookVector
  local right=cam.CFrame.RightVector
  local rx=delta:Dot(right); local rz=delta:Dot(forward)
  local scale=math.min(1,math.sqrt(rx*rx+rz*rz)/30)
  local angle=math.atan2(rx,-rz)
  local x=math.sin(angle)*scale*.43; local y=-math.cos(angle)*scale*.43
  dot.Position=UDim2.fromScale(.5+x,.5+y); dot.Visible=true
 end
 for i=#positions+1,#radarDots do radarDots[i].Visible=false end
end
local ammo=makeLabel(gui,"Ammo","Pistola 12 / 48",18,UDim2.new(1,-18,1,-42),Vector2.new(1,1)); ammo.TextXAlignment=Enum.TextXAlignment.Right
local abilities=makeLabel(gui,"Abilities","Q Dash | E Onda | F Torreta | C Furia",13,UDim2.new(.5,0,1,-12),Vector2.new(.5,1)); abilities.TextXAlignment=Enum.TextXAlignment.Center; abilities.Size=UDim2.fromOffset(500,24)
local cross=makeLabel(gui,"Crosshair","+ ",26,UDim2.fromScale(.5,.5),Vector2.new(.5,.5)); cross.Size=UDim2.fromOffset(30,30); cross.TextXAlignment=Enum.TextXAlignment.Center
local notice=makeLabel(gui,"Notice","",22,UDim2.new(.5,0,.23,0),Vector2.new(.5,.5)); notice.TextXAlignment=Enum.TextXAlignment.Center; notice.Size=UDim2.fromOffset(600,40)
local shop=makePanel("Shop",UDim2.fromScale(.5,.5),UDim2.fromOffset(500,500)); shop.AnchorPoint=Vector2.new(.5,.5); shop.Visible=false
local pausePanel=makePanel("Pause",UDim2.fromScale(.5,.5),UDim2.fromOffset(340,180)); pausePanel.AnchorPoint=Vector2.new(.5,.5); pausePanel.Visible=false
local pauseTitle=makeLabel(pausePanel,"Title","PAUSA",26,UDim2.fromOffset(20,24)); pauseTitle.TextXAlignment=Enum.TextXAlignment.Center; pauseTitle.Size=UDim2.new(1,-40,0,40)
local resume=Instance.new("TextButton"); resume.Size=UDim2.fromOffset(180,42); resume.Position=UDim2.new(.5,0,1,-28); resume.AnchorPoint=Vector2.new(.5,1); resume.Text="CONTINUAR"; resume.Font=Enum.Font.GothamBold; resume.TextSize=15; resume.TextColor3=Color3.new(1,1,1); resume.BackgroundColor3=Color3.fromRGB(190,35,55); resume.Parent=pausePanel
local resumeCorner=Instance.new("UICorner"); resumeCorner.CornerRadius=UDim.new(0,6); resumeCorner.Parent=resume
local shopTitle=makeLabel(shop,"Title","TIENDA",20,UDim2.fromOffset(14,8)); shopTitle.Size=UDim2.new(1,-28,0,30)
local shopList=Instance.new("ScrollingFrame"); shopList.Position=UDim2.fromOffset(12,48); shopList.Size=UDim2.new(1,-24,1,-60); shopList.BackgroundTransparency=1; shopList.BorderSizePixel=0; shopList.ScrollBarThickness=5; shopList.Parent=shop
local layout=Instance.new("UIListLayout"); layout.Padding=UDim.new(0,5); layout.Parent=shopList
layout:GetPropertyChangedSignal("AbsoluteContentSize"):Connect(function() shopList.CanvasSize=UDim2.fromOffset(0,layout.AbsoluteContentSize.Y+8) end)
local function addButton(text:string,fn:()->())
 local b=Instance.new("TextButton"); b.Size=UDim2.new(1,-8,0,36); b.BackgroundColor3=Color3.fromRGB(31,38,48); b.TextColor3=Color3.fromRGB(240,246,252); b.Text=text; b.TextSize=13; b.Font=Enum.Font.GothamMedium; b.Parent=shopList
 local c=Instance.new("UICorner"); c.CornerRadius=UDim.new(0,5); c.Parent=b
 b.Activated:Connect(fn)
end
local function populateShop()
 for _,v in ipairs(shopList:GetChildren()) do if v:IsA("TextButton") then v:Destroy() end end
 for i,w in ipairs(Config.Weapons) do
  if not (current.Unlocked and current.Unlocked[i]) then addButton("Comprar "..w.Name.."  |  $"..w.Price,function() Action:FireServer("Shop",{Category="weapon",Key=tostring(i)}) end) end
  for _,u in ipairs(Config.WeaponUpgrades) do addButton(w.Name.." - "..u.Name.."  |  $"..u.Cost,function() Action:FireServer("Shop",{Category="weapon",Key=u.Key,Index=i}) end) end
 end
 for _,p in ipairs(Config.Perks) do addButton(p.Name.."  |  $"..p.Cost,function() Action:FireServer("Shop",{Category="perk",Key=p.Key}) end) end
 for key,a in pairs(Config.Abilities) do local cost=({dash=200,onda=250,torreta=300,furia=300})[key]; addButton("Mejorar "..key.."  |  $"..cost,function() Action:FireServer("Shop",{Category="ability",Key=key}) end) end
 for _,s in ipairs(Config.Supplies) do addButton(s.Name.."  |  $"..s.Cost,function() Action:FireServer("Shop",{Category="supply",Key=s.Key}) end) end
end
local function togglePause(value:boolean)
 paused=value; pausePanel.Visible=value
 Action:FireServer("Pause",value)
 if value then UIS.MouseBehavior=Enum.MouseBehavior.Default; UIS.MouseIconEnabled=true
 else UIS.MouseBehavior=Enum.MouseBehavior.LockCenter; UIS.MouseIconEnabled=false end
end
resume.Activated:Connect(function() togglePause(false) end)
local function toggleShop(value:boolean)
 shopOpen=value; shop.Visible=value
 if value then populateShop(); UIS.MouseBehavior=Enum.MouseBehavior.Default; UIS.MouseIconEnabled=true
 else UIS.MouseBehavior=Enum.MouseBehavior.LockCenter; UIS.MouseIconEnabled=false end
end
State.OnClientEvent:Connect(function(s:any)
 current=s
 stats.Text=string.format("Puntos: %d | Creditos: $%d | Record: %d",s.Points or 0,s.Credits or 0,s.Record or 0)
 wave.Text=string.format("OLEADA %d | Enemigos: %d",s.Wave or 0,s.Enemies or 0)
 if (s.Intermission or 0)>0 then wave.Text=wave.Text.." | Próxima: "..math.ceil(s.Intermission).."s (B tienda / ENTER)" end
 health.Text=string.format("Vida: %d / %d",s.Health or 0,s.MaxHealth or 100)
 healthFill.Size=UDim2.fromScale(math.clamp((s.Health or 0)/math.max(1,s.MaxHealth or 100),0,1),1)
 local i=s.Weapon or 1; local w=Config.Weapons[i]
 ammo.Text=string.format("%s [%d]  %d / %d",w.Name,i,(s.Magazine and s.Magazine[i]) or 0,(s.Reserve and s.Reserve[i]) or 0)
 local cd=s.Cooldowns or {}
 abilities.Text=string.format("Q Dash %ds | E Onda %ds | F Torreta %ds | C Furia %ds",cd.dash or 0,cd.onda or 0,cd.torreta or 0,cd.furia or 0)
 if shopOpen then shopTitle.Text="TIENDA | Creditos: $"..(s.Credits or 0) end
end)
Notice.OnClientEvent:Connect(function(message:string,color:Color3?)
 notice.Text=message; if color then notice.TextColor3=color end
 task.delay(2.5,function() if notice.Text==message then notice.Text="" end end)
end)
local function fire()
 if not shopOpen and not paused and workspace.CurrentCamera then Action:FireServer("Fire",workspace.CurrentCamera.CFrame.LookVector) end
end
local function sprint(value:boolean) if sprinting~=value then sprinting=value; Action:FireServer("Sprint",value) end end
UIS.InputBegan:Connect(function(input,processed)
 if processed then return end
 if input.KeyCode==Enum.KeyCode.Escape or input.KeyCode==Enum.KeyCode.P then if shopOpen then toggleShop(false) else togglePause(not paused) end
 elseif paused then return
 elseif input.UserInputType==Enum.UserInputType.MouseButton1 then firing=true; fire()
 elseif input.KeyCode==Enum.KeyCode.R then Action:FireServer("Reload")
 elseif input.KeyCode==Enum.KeyCode.LeftShift then sprint(true)
 elseif input.KeyCode==Enum.KeyCode.Q then Action:FireServer("Ability","dash")
 elseif input.KeyCode==Enum.KeyCode.E then Action:FireServer("Ability","onda")
 elseif input.KeyCode==Enum.KeyCode.F then Action:FireServer("Ability","torreta")
 elseif input.KeyCode==Enum.KeyCode.C then Action:FireServer("Ability","furia")
 elseif input.KeyCode==Enum.KeyCode.B and (current.Intermission or 0)>0 then toggleShop(not shopOpen)
 elseif input.KeyCode==Enum.KeyCode.Return then if shopOpen then toggleShop(false) elseif (current.Intermission or 0)>0 then Action:FireServer("StartWave") end
 elseif input.KeyCode.Value>=Enum.KeyCode.One.Value and input.KeyCode.Value<=Enum.KeyCode.Five.Value then Action:FireServer("Equip",input.KeyCode.Value-Enum.KeyCode.One.Value+1) end
end)
UIS.InputEnded:Connect(function(input)
 if input.UserInputType==Enum.UserInputType.MouseButton1 then firing=false elseif input.KeyCode==Enum.KeyCode.LeftShift then sprint(false) end
end)
UIS.InputChanged:Connect(function(input)
 if input.UserInputType==Enum.UserInputType.MouseWheel and current.Weapon then local i=((current.Weapon+(if input.Position.Z>0 then 1 else -1)-1)%#Config.Weapons)+1; Action:FireServer("Equip",i) end
end)
player.CharacterAdded:Connect(function() toggleShop(false); togglePause(false); UIS.MouseBehavior=Enum.MouseBehavior.LockCenter; UIS.MouseIconEnabled=false end)
UIS.MouseBehavior=Enum.MouseBehavior.LockCenter; UIS.MouseIconEnabled=false

-- Viewmodel local: no replica piezas al servidor.
player.CameraMode=Enum.CameraMode.LockFirstPerson
local viewmodel=Instance.new("Model"); viewmodel.Name="OUE_Viewmodel"; viewmodel.Parent=workspace.CurrentCamera
local function vmPart(name:string,size:Vector3,color:Color3,offset:CFrame):Part
 local p=Instance.new("Part"); p.Name=name; p.Size=size; p.Color=color; p.Material=Enum.Material.Metal
 p.Anchored=true; p.CanCollide=false; p.CanTouch=false; p.CanQuery=false; p.CastShadow=false; p.CFrame=workspace.CurrentCamera.CFrame*offset; p.Parent=viewmodel; return p
end
local vmBody=vmPart("Receiver",Vector3.new(.22,.18,.62),Color3.fromRGB(48,50,56),CFrame.new(.48,-.38,-.8))
local vmBarrel=vmPart("Barrel",Vector3.new(.09,.09,.48),Color3.fromRGB(18,19,22),CFrame.new(.48,-.34,-1.3))
local vmGrip=vmPart("Grip",Vector3.new(.12,.28,.16),Color3.fromRGB(28,29,32),CFrame.new(.48,-.55,-.65))
local vmMuzzle=vmPart("Muzzle",Vector3.new(.13,.13,.08),Color3.fromRGB(90,90,95),CFrame.new(.48,-.34,-1.56))
local vmFlash=vmPart("MuzzleFlash",Vector3.new(.25,.25,.25),Color3.fromRGB(255,190,70),CFrame.new(.48,-.34,-1.68))
vmFlash.Shape=Enum.PartType.Ball; vmFlash.Material=Enum.Material.Neon; vmFlash.Transparency=1
local lastVmWeapon=0
local function updateViewmodel()
 local cam=workspace.CurrentCamera; if not cam then return end
 if current.Weapon and current.Weapon~=lastVmWeapon then
  lastVmWeapon=current.Weapon
  local weapon=Config.Weapons[lastVmWeapon]
  vmBody.Color=weapon.Color
  vmBody.Size=Vector3.new(.22,.18,math.clamp(weapon.Size.Z*.9,.35,1))
  vmBarrel.Size=Vector3.new(.09,.09,math.max(.25,weapon.Size.Z*.7))
 end
 local base=CFrame.new(.48,-.38,-.8)
 vmBody.CFrame=cam.CFrame*base
 vmBarrel.CFrame=cam.CFrame*CFrame.new(.48,-.34,-1.3)
 vmGrip.CFrame=cam.CFrame*CFrame.new(.48,-.55,-.65)
 vmMuzzle.CFrame=cam.CFrame*CFrame.new(.48,-.34,-1.56)
 vmFlash.CFrame=cam.CFrame*CFrame.new(.48,-.34,-1.7)
end

RunService.RenderStepped:Connect(function() updateViewmodel(); if firing and not shopOpen and not paused then local w=Config.Weapons[current.Weapon or 1]; if w and w.Automatic then fire() end end end)
