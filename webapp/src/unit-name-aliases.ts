// Maps the raw build-order entry name (as sc2reader emits it) to the
// canonical display name used as a key in unit-icon-map.json.
// Only entries that DIFFER between the two formats need to live here —
// names that already match the icon map key (e.g. "Marine", "Hatchery")
// fall through unchanged.
export const NAME_TO_CANONICAL: Record<string, string> = {
  // Terran structures
  CommandCenter: "Command Center",
  EngineeringBay: "Engineering Bay",
  FusionCore: "Fusion Core",
  GhostAcademy: "Ghost Academy",
  MissileTurret: "Missile Turret",
  OrbitalCommand: "Orbital Command",
  PlanetaryFortress: "Planetary Fortress",
  SensorTower: "Sensor Tower",
  SupplyDepot: "Supply Depot",
  TechLab: "Tech Lab",
  BarracksTechLab: "Tech Lab",
  FactoryTechLab: "Tech Lab",
  StarportTechLab: "Tech Lab",
  Reactor: "Reactor",
  BarracksReactor: "Reactor",
  FactoryReactor: "Reactor",
  StarportReactor: "Reactor",
  // Zerg structures
  BanelingNest: "Baneling Nest",
  CreepTumor: "Creep Tumor",
  EvolutionChamber: "Evolution Chamber",
  GreaterSpire: "Greater Spire",
  HydraliskDen: "Hydralisk Den",
  InfestationPit: "Infestation Pit",
  LurkerDen: "Lurker Den",
  NydusNetwork: "Nydus Network",
  NydusCanal: "Nydus Canal",
  RoachWarren: "Roach Warren",
  SpawningPool: "Spawning Pool",
  SpineCrawler: "Spine Crawler",
  SporeCrawler: "Spore Crawler",
  UltraliskCavern: "Ultralisk Cavern",
  // Protoss structures
  CyberneticsCore: "Cybernetics Core",
  DarkShrine: "Dark Shrine",
  FleetBeacon: "Fleet Beacon",
  PhotonCannon: "Photon Cannon",
  RoboticsBay: "Robotics Bay",
  RoboticsFacility: "Robotics Facility",
  ShieldBattery: "Shield Battery",
  TemplarArchives: "Templar Archives",
  TwilightCouncil: "Twilight Council",
  WarpGate: "Warp Gate",
};

export function canonicalUnitName(name: string): string {
  if (!name) return "";
  return NAME_TO_CANONICAL[name] ?? name;
}
