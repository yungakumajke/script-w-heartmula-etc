local JOB_DIR = reaper.GetExtState("AI_MUSIC", "JOB_DIR")
local POLL_SEC = 1.0
local LAST_CHECK = 0

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

local function norm(s)
  s = tostring(s or ""):lower()
  s = s:gsub("%.wav$", "")
  s = s:gsub("%.flac$", "")
  s = s:gsub("%.mp3$", "")
  s = s:gsub("%.aiff$", "")
  s = s:gsub("%s+", "")
  return s
end

local function get_take_name(take)
  local ok, name = reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", "", false)
  if ok and name and name ~= "" then return trim(name) end
  return nil
end

local function get_track_name(track)
  local ok, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  if ok and name and name ~= "" then return trim(name) end
  return nil
end

local function replace_source(take, path)
  if reaper.BR_SetTakeSourceFromFile then
    return reaper.BR_SetTakeSourceFromFile(take, path, false)
  end
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then return false end
  return reaper.SetMediaItemTake_Source(take, src)
end

local function find_file(folder, base)
  local exts = {".wav", ".flac", ".mp3", ".aiff"}
  for _, ext in ipairs(exts) do
    local p = folder .. "/" .. base .. ext
    if exists(p) then return p end
  end
  return nil
end

local function process_job()
  if JOB_DIR == nil or JOB_DIR == "" then return end
  local count = reaper.CountSelectedMediaItems(0)
  if count == 0 then return end

  reaper.Undo_BeginBlock()
  reaper.PreventUIRefresh(1)

  for i = 0, count - 1 do
    local item = reaper.GetSelectedMediaItem(0, i)
    if item then
      local take = reaper.GetActiveTake(item)
      if take and not reaper.TakeIsMIDI(take) then
        local track = reaper.GetMediaItemTrack(item)
        local name = get_take_name(take) or get_track_name(track)
        if name then
          local file = find_file(JOB_DIR, norm(name))
          if file then
            replace_source(take, file)
          end
        end
      end
    end
  end

  reaper.PreventUIRefresh(-1)
  reaper.UpdateArrange()
  reaper.Undo_EndBlock("AI Music Watcher Update", -1)
end

local function main()
  local now = reaper.time_precise()
  if now - LAST_CHECK >= POLL_SEC then
    LAST_CHECK = now
    process_job()
  end
  reaper.defer(main)
end

if JOB_DIR == nil or JOB_DIR == "" then
  reaper.ShowMessageBox("Set ExtState AI_MUSIC/JOB_DIR first.", "Error", 0)
else
  main()
end