# Auto-generated by ChatGPT from the UISP API Swagger file available here
# https://uisp.mesh.nycmesh.net/nms/api-docs/swagger.json
# with small manual tweaks to correct its mistakes. If these are wrong feel free to @ me
# In particular I think the UISP devs phoned it in on their documentation for what
# fields are required, so lots of stuff that's probably always there
# is marked NotRequired


from typing import Dict, List, Literal, NotRequired, Optional, TypedDict

from meshapi.types.uisp_api.literals import (
    CountryCodeLiteral,
    CountryLiteral,
    DeviceTypeLiteral,
    ModelLiteral,
    PlatformNameLiteral,
    RoleLiteral,
    StatusLiteral,
)


class Device(TypedDict):
    aircube: NotRequired["DeviceAirCube"]
    airfiber: Dict  # Deprecated
    airmax: Dict  # Deprecated
    attributes: NotRequired["DeviceAttributes"]
    configuration: NotRequired["Configuration"]
    discovery: NotRequired["Discovery"]
    enabled: bool
    eswitch: NotRequired["Eswitch"]
    features: NotRequired["Features"]
    firmware: NotRequired["DeviceFirmware"]
    identification: NotRequired["DeviceIdentification"]
    interfaces: NotRequired[List["DeviceInterfaceSchema"]]
    ipAddress: str
    ipAddressList: NotRequired[List[str]]
    latestBackup: NotRequired["LatestBackup"]
    location: NotRequired["DeviceLocation"]
    meta: NotRequired["DeviceMeta"]
    mode: NotRequired[str]
    overview: NotRequired["DeviceOverview"]
    uisps: NotRequired["Uisps"]
    upgrade: NotRequired["DeviceUpgrade"]
    uplinkDevice: NotRequired["DeviceUplinkDevice"]
    ux: NotRequired["Ux"]


class DeviceAirCube(TypedDict):
    apDevice: NotRequired["APDevice"]
    dhcpLeases: NotRequired[List["DHCPLease"]]
    lanIp: NotRequired[str]
    mgmtIp: NotRequired[str]
    poe: NotRequired[bool]
    wanIp: NotRequired[str]
    wifi2Ghz: NotRequired["Wifi"]
    wifi5Ghz: NotRequired["Wifi"]
    wifiMode: NotRequired[Literal["ap", "mesh"]]


class DeviceAttributes(TypedDict):
    apDevice: NotRequired["APDevice"]
    backupNetAddress: NotRequired[str]
    backupNetQuotaCurrent: NotRequired[int]
    backupNetQuotaMaximal: NotRequired[int]
    cardStatus: NotRequired[Literal["unknown", "absent", "present"]]
    country: NotRequired[CountryLiteral]
    countryCode: NotRequired[int]
    dyingGasp: NotRequired[bool]
    gatewayId: NotRequired[str]
    hasGatewayInterfaceAvailable: NotRequired[bool]
    imei: NotRequired[str]
    isAxCompatible: NotRequired[bool]
    isGatewaySupported: NotRequired[bool]
    operator: NotRequired[str]
    parentId: NotRequired[str]
    pinAttemptsRemaining: NotRequired[int]
    pinStatus: NotRequired[Literal["disabled", "required", "unlocked", "blocked", "unknown"]]
    regStatus: NotRequired[Literal["unknown", "not_registered", "searching", "registered", "connected", "denied"]]
    secondarySsid: NotRequired[str]
    series: NotRequired[str]
    signalLevel: NotRequired[float]
    signalStrength: NotRequired[float]
    smsQuotaCurrent: NotRequired[int]
    smsQuotaMaximal: NotRequired[int]
    ssid: NotRequired[str]
    technology: NotRequired[Literal["gsm", "umts", "tdscdma", "lte", "cdma"]]


class Configuration(TypedDict):
    createdAt: NotRequired[str]  # ISO 8601 date-time str
    hash: NotRequired[str]
    id: NotRequired[str]
    status: NotRequired[Literal["applying", "applied"]]


class Discovery(TypedDict):
    configured: NotRequired[bool]
    error: NotRequired[str]
    isProcessing: NotRequired[bool]
    protocol: NotRequired[str]
    snmpCommunity: NotRequired[str]
    status: NotRequired[str]
    visibleBy: NotRequired["VisibleBy"]


class Eswitch(TypedDict):
    vlans: NotRequired["Vlans"]


class Features(TypedDict):
    has60GhzRadio: NotRequired[bool]
    hasBackupAntenna: NotRequired[bool]
    isSupportRouter: NotRequired[bool]
    isUdapiSpeedTestSupported: NotRequired[bool]
    isUsingUdapiUpdaters: NotRequired[bool]


class DeviceFirmware(TypedDict):
    compatible: NotRequired[bool]
    current: str
    latest: str
    latestOnCurrentMajorVersion: str
    latestOver: str
    prospective: str
    semver: NotRequired["Semver"]
    upgradeRecommendedToVersion: str


class DeviceIdentification(TypedDict):
    authorized: NotRequired[bool]
    bridgeVersion: NotRequired[str]
    category: NotRequired[Literal["optical", "wired", "wireless", "accessories"]]
    displayName: NotRequired[str]
    firmwareVersion: NotRequired[str]
    hostname: NotRequired[str]
    id: str
    ip: NotRequired[str]
    mac: NotRequired[str]
    model: NotRequired[ModelLiteral]
    modelName: NotRequired[str]
    name: NotRequired[str]
    platformId: NotRequired[str]
    platformName: NotRequired[PlatformNameLiteral]
    role: NotRequired[RoleLiteral]
    serialNumber: NotRequired[str]
    site: NotRequired["Site"]
    started: NotRequired[str]  # ISO 8601 date-time str
    status: NotRequired[StatusLiteral]
    subsystemId: NotRequired[str]
    systemName: NotRequired[str]
    type: NotRequired[DeviceTypeLiteral]
    udapiVersion: NotRequired[str]
    updated: NotRequired[str]  # ISO 8601 date-time str
    vendor: NotRequired[str]
    vendorName: NotRequired[str]
    wanInterfaceId: NotRequired[str]


class LatestBackup(TypedDict):
    id: str
    timestamp: str  # ISO 8601 date-time str


class DeviceLocation(TypedDict):
    altitude: float
    elevation: float
    heading: NotRequired[float]
    latitude: float
    longitude: float
    magneticHeading: float
    roll: float
    tilt: float


class DeviceMeta(TypedDict):
    activeAction: NotRequired[Literal["restarting", "removing", "updatingFirmware", "generatingSupportFile"]]
    alias: NotRequired[str]
    customIpAddress: NotRequired[str]
    failedDecryptionAt: NotRequired[str]  # ISO 8601 date-time str
    failedMessageDecryption: bool
    firmwareCompatibility: Literal["obsolete", "compatible", "prospective", "upgradable"]
    maintenance: bool
    maintenanceEnabledAt: NotRequired[str]  # ISO 8601 date-time str
    note: NotRequired[str]
    restartTimestamp: str  # ISO 8601 date-time str


class DeviceOverview(TypedDict):
    antenna: NotRequired["Antenna"]
    batteryCapacity: NotRequired[float]
    batteryTime: NotRequired[float]
    biasCurrent: NotRequired[float]
    canUpgrade: NotRequired[bool]
    channelWidth: NotRequired[float]
    consumption: NotRequired[float]
    cpu: NotRequired[float]
    createdAt: NotRequired[str]  # ISO 8601 date-time str
    dfsLockouts: NotRequired[List[float]]
    distance: NotRequired[float]
    downlinkCapacity: NotRequired[int]
    downlinkUtilization: NotRequired[float]
    frequency: NotRequired[float]
    isLocateRunning: NotRequired[bool]
    keyExchangeStatus: NotRequired[Literal["pending", "complete"]]
    lastSeen: NotRequired[Optional[str]]  # ISO 8601 date-time str
    linkActiveStationsCount: NotRequired[float]
    linkOutageScore: NotRequired[float]
    linkScore: NotRequired["LinkScore"]
    linkStationsCount: NotRequired[float]
    mainInterfaceSpeed: NotRequired["MainLanInterfaceSpeed"]
    maximalPower: NotRequired[float]
    outageScore: NotRequired[float]
    outputPower: NotRequired[float]
    outputPowers: NotRequired[List[float]]
    powerStatus: NotRequired[float]
    psu: NotRequired[List["PSU"]]
    ram: NotRequired[float]
    remoteSignalMax: NotRequired[float]
    runningOnBattery: NotRequired[bool]
    serviceTime: NotRequired[float]
    serviceUptime: NotRequired[float]
    signal: NotRequired[float]
    signalMax: NotRequired[float]
    stationsCount: NotRequired[float]
    status: NotRequired[str]
    temperature: NotRequired[float]
    theoreticalDownlinkCapacity: NotRequired[int]
    theoreticalTotalCapacity: NotRequired[int]
    theoreticalUplinkCapacity: NotRequired[int]
    totalCapacity: NotRequired[int]
    transmitPower: NotRequired[float]
    uplinkCapacity: NotRequired[int]
    uplinkUtilization: NotRequired[float]
    uptime: NotRequired[float]
    voltage: NotRequired[float]
    wirelessActiveInterfaceIds: NotRequired[List[str]]
    wirelessMode: NotRequired[
        Literal[
            "ap",
            "ap-ptp",
            "ap-ptmp",
            "ap-ptmp-airmax",
            "ap-ptmp-airmax-mixed",
            "ap-ptmp-airmax-ac",
            "sta",
            "sta-ptp",
            "sta-ptmp",
            "aprepeater",
            "repeater",
            "mesh",
        ]
    ]


class Uisps(TypedDict):
    vlans: NotRequired["Vlans"]


class DeviceUpgrade(TypedDict):
    firmware: "Firmware"
    firmwareVersion: str
    progress: float
    status: str
    upgradeInMaintenanceWindow: NotRequired[bool]


class DeviceUplinkDevice(TypedDict):
    identification: NotRequired["DeviceIdentification"]


class Ux(TypedDict):
    cloudDeviceToken: str
    meshing: NotRequired[List["OtherDevice"]]
    uplink: NotRequired["Uplink"]


class APDevice(TypedDict):
    firmware: NotRequired["DeviceFirmware"]
    id: NotRequired[str]
    model: NotRequired[ModelLiteral]
    name: NotRequired[str]
    series: NotRequired[str]
    siteId: NotRequired[str]
    type: NotRequired[str]


class DeviceInterfaceSchema(TypedDict):
    addresses: NotRequired[List["Address"]]
    bridge: NotRequired[str]
    canDisplayStatistics: NotRequired[bool]
    capabilities: NotRequired["Capabilities"]
    dhcp6PDRequestSize: NotRequired[int]
    dhcp6PDUseFromInterface: NotRequired[str]
    dhcp6PDUseSize: NotRequired[int]
    enabled: NotRequired[bool]
    identification: "InterfaceIdentification"
    isBridgedPort: NotRequired[bool]
    isSwitchedPort: NotRequired[bool]
    lag: NotRequired["Lag"]
    mssClamping: NotRequired[bool]
    mtu: NotRequired[str]
    ospf: NotRequired["InterfaceOspf"]
    poe: NotRequired["InterfacePoe"]
    port: NotRequired["Port"]
    pppoe: NotRequired[str]
    proxyARP: NotRequired[str]
    sfp: NotRequired[str]
    speed: NotRequired[str]
    speeds: NotRequired["InterfaceSpeeds"]
    stations: NotRequired[List["Station"]]
    statistics: NotRequired["InterfaceStatistics"]
    status: NotRequired["InterfaceStatus"]
    switch: NotRequired["Switch"]
    switchedPorts: NotRequired[List["SwitchedPort"]]
    visible: NotRequired[bool]
    vlan: NotRequired["Vlan"]
    wireless: NotRequired["Wireless"]


class DHCPLease(TypedDict):
    hostname: NotRequired[str]
    ip: NotRequired[str]
    mac: NotRequired[str]
    timeout: NotRequired[float]


class Wifi(TypedDict):
    authentication: NotRequired[Literal["psk", "psk2", "ent", "none"]]
    available: NotRequired[bool]
    channel: NotRequired[float]
    channelWidth: NotRequired[int]
    country: NotRequired[CountryCodeLiteral]
    enabled: NotRequired[bool]
    encryption: NotRequired[Literal["wep", "wpa", "wpa-psk", "wpa2", "wpa2-eap", "enabled", "none"]]
    frequency: NotRequired[float]
    isChannelAuto: NotRequired[bool]
    key: NotRequired[str]
    mac: NotRequired[str]
    mode: NotRequired[Literal["ap", "mesh"]]
    ssid: NotRequired[str]
    stationsCount: NotRequired[float]
    txPower: NotRequired[float]


class VisibleBy(TypedDict):
    id: str
    model: ModelLiteral
    name: str
    type: DeviceTypeLiteral


class Vlans(TypedDict):
    interface: NotRequired[Dict]
    vlanId: NotRequired[Dict]


class Semver(TypedDict):
    current: NotRequired["Version"]
    latest: NotRequired["Version"]
    latestOnCurrentMajorVersion: NotRequired["Version"]
    latestOver: NotRequired["Version"]


class Site(TypedDict):
    id: str
    name: NotRequired[str]
    parent: NotRequired[Dict]
    status: Literal["active", "disconnected", "inactive", "unknown"]
    type: Literal["site", "endpoint"]


class Antenna(TypedDict):
    builtIn: NotRequired[bool]
    cableLoss: NotRequired[float]
    gain: NotRequired[float]
    id: NotRequired[int]
    name: NotRequired[str]


class LinkScore(TypedDict):
    airTime: NotRequired[float]
    airTimeScore: NotRequired[float]
    downlinkScore: NotRequired[float]
    linkScore: NotRequired[float]
    linkScoreHint: NotRequired[str]
    score: NotRequired[float]
    scoreMax: NotRequired[float]
    theoreticalDownlinkCapacity: NotRequired[int]
    theoreticalTotalCapacity: NotRequired[int]
    theoreticalUplinkCapacity: NotRequired[int]
    uplinkScore: NotRequired[float]


class MainLanInterfaceSpeed(TypedDict):
    availableSpeed: NotRequired[str]
    interfaceId: NotRequired[str]


class PSU(TypedDict):
    batteryCapacity: NotRequired[float]
    batteryCapacityConfigured: NotRequired[float]
    batteryCapacityEstimated: NotRequired[float]
    batteryTime: NotRequired[float]
    batteryType: NotRequired[str]
    connected: NotRequired[bool]
    maxChargingPower: NotRequired[float]
    power: NotRequired[float]
    psuType: NotRequired[str]
    voltage: NotRequired[float]


class Version(TypedDict):
    major: int
    minor: int
    patch: int
    order: str
    prerelease: NotRequired[List[str]]


class Firmware(Version):
    upgradeRecommendedToVersion: NotRequired[str]


class Address(TypedDict):
    cidr: str
    origin: NotRequired[Literal["dhcp", "slaac", "link-local", "static", "ppp"]]
    type: Literal["dynamic", "static", "pppoe", "dhcp", "dhcpv6"]
    version: NotRequired[Literal["v4", "v6"]]


class OtherDevice(TypedDict):
    clients: NotRequired[int]
    model: NotRequired[ModelLiteral]
    name: NotRequired[str]
    version: NotRequired[str]
    wiFiExperience: NotRequired[float]


class Uplink(TypedDict):
    rxBytes: NotRequired[int]
    rxRate: NotRequired[int]
    txBytes: NotRequired[int]
    txRate: NotRequired[int]


class Capabilities(TypedDict):
    loadBalanceValues: NotRequired[List[str]]
    supportAutoEdge: NotRequired[bool]
    supportCableTest: NotRequired[bool]
    supportReset: NotRequired[bool]


class InterfaceIdentification(TypedDict):
    connectedMac: NotRequired[str]
    description: NotRequired[str]
    displayName: NotRequired[str]
    mac: NotRequired[str]
    macOverride: NotRequired[str]
    name: NotRequired[str]
    position: NotRequired[int]
    type: NotRequired[str]


class Lag(TypedDict):
    dhcpSnooping: NotRequired[bool]
    includeVlans: NotRequired[str]
    linkTrap: NotRequired[bool]
    loadBalance: NotRequired[str]
    mode: NotRequired[str]
    ports: NotRequired[List[str]]
    static: NotRequired[bool]
    stp: NotRequired["Stp"]
    vlanNative: NotRequired[int]


class InterfaceOspf(TypedDict):
    ospfCapable: NotRequired[bool]
    ospfConfig: "OspfConfig"


class InterfacePoe(TypedDict):
    capacities: NotRequired[List[str]]
    output: NotRequired[
        Literal["off", "active", "24v", "27v", "48v", "54v", "24v-4pair", "27v-4pair", "54v-4pair", "pthru"]
    ]


class Port(TypedDict):
    dhcpSnooping: NotRequired[bool]
    flowControl: NotRequired[bool]
    isolated: NotRequired[bool]
    pingWatchdog: NotRequired["PingWatchdog"]
    routed: NotRequired[bool]
    speedLimit: NotRequired["SpeedLimit"]
    stp: NotRequired["Stp"]


class InterfaceSpeeds(TypedDict):
    capacities: NotRequired[List[str]]
    speed: NotRequired[str]


class Station(TypedDict):
    connected: NotRequired[bool]
    connectionTime: NotRequired[int]
    deviceIdentification: NotRequired["DeviceIdentification"]
    distance: NotRequired[int]
    downlinkAirTime: NotRequired[float]
    downlinkCapacity: NotRequired[int]
    firmware: NotRequired["DeviceFirmware"]
    interfaceId: NotRequired[str]
    ipAddress: NotRequired[str]
    latency: NotRequired[int]
    mac: NotRequired[str]
    model: NotRequired[ModelLiteral]
    modelName: NotRequired[str]
    name: NotRequired[str]
    noiseFloor: NotRequired[int]
    radio: NotRequired[str]
    rxBytes: NotRequired[int]
    rxChain: NotRequired[List[int]]
    rxChainIdeal: NotRequired[List[int]]
    rxChainMask: NotRequired[int]
    rxMcs: NotRequired[str]
    rxMcsIdeal: NotRequired[str]
    rxMcsIndex: NotRequired[str]
    rxMcsIndexIdeal: NotRequired[str]
    rxModulation: NotRequired[str]
    rxRate: NotRequired[int]
    rxSignal: NotRequired[int]
    rxSignalIdeal: NotRequired[int]
    statistics: NotRequired["Statistics"]
    systemName: NotRequired[str]
    timestamp: NotRequired[str]
    txBytes: NotRequired[int]
    txChain: NotRequired[List[int]]
    txChainIdeal: NotRequired[List[int]]
    txChainMask: NotRequired[int]
    txMcs: NotRequired[str]
    txMcsIdeal: NotRequired[str]
    txMcsIndex: NotRequired[str]
    txMcsIndexIdeal: NotRequired[str]
    txModulation: NotRequired[str]
    txRate: NotRequired[int]
    txSignal: NotRequired[int]
    txSignalIdeal: NotRequired[int]
    uplinkAirTime: NotRequired[float]
    uplinkCapacity: NotRequired[int]
    uptime: NotRequired[int]
    vendor: NotRequired[str]
    vendorName: NotRequired[str]


class InterfaceStatistics(TypedDict):
    dropped: NotRequired[float]
    errors: NotRequired[float]
    poePower: NotRequired[float]
    rxMcs: NotRequired[float]
    rxbytes: NotRequired[float]
    rxrate: NotRequired[float]
    txMcs: NotRequired[float]
    txbytes: NotRequired[float]
    txrate: NotRequired[float]


class InterfaceStatus(TypedDict):
    currentSpeed: NotRequired[str]
    description: NotRequired[str]
    plugged: NotRequired[bool]
    speed: NotRequired[str]
    status: NotRequired[str]


class Switch(TypedDict):
    ports: List["Port1"]
    vlanCapable: bool
    vlanEnabled: bool


class SwitchedPort(TypedDict):
    id: NotRequired[int]
    key: NotRequired[str]


class Vlan(TypedDict):
    egressQoSMapExternal: NotRequired[int]
    id: NotRequired[int]
    parent: NotRequired[str]


class Wireless(TypedDict):
    antenna: NotRequired["Antenna"]
    channelWidth: int
    dfsLockouts: List[float]
    dfsTimeRemaining: float
    dfsTimeTotal: float
    dlRatio: int
    frameLength: float
    frequency: float
    frequencyBand: NotRequired[Literal["2.4GHz", "3GHz", "4GHz", "5GHz", "11GHz", "24GHz", "60GHz"]]
    key: str
    maxTxPower: NotRequired[float]
    minTxPower: NotRequired[float]
    noiseFloor: int
    security: Literal["wep", "wpa", "wpa-psk", "wpa2", "wpa2-eap", "enabled", "none"]
    serviceUptime: NotRequired[float]
    ssid: str
    transmitEirp: NotRequired[float]
    transmitPower: NotRequired[float]
    waveAiEnabled: NotRequired[bool]


class Stp(TypedDict):
    edgePort: NotRequired[Literal["auto", "enable", "disable"]]
    enabled: NotRequired[bool]
    pathCost: NotRequired[float]
    portPriority: NotRequired[float]
    state: NotRequired[Literal["disabled", "discarding", "listening", "learning", "forwarding"]]


class OspfConfig(TypedDict):
    auth: NotRequired[str]
    authKey: NotRequired[str]
    authKeysMD5: NotRequired[List["AuthKeyMD5"]]
    cost: NotRequired[str]
    enabled: NotRequired[bool]


class PingWatchdog(TypedDict):
    address: NotRequired[str]
    enabled: NotRequired[bool]
    failureCount: NotRequired[int]
    interval: NotRequired[float]
    offDelay: NotRequired[float]
    startDelay: NotRequired[float]


class SpeedLimit(TypedDict):
    enabled: NotRequired[bool]
    rx: NotRequired[float]
    tx: NotRequired[float]


class Statistics(TypedDict):
    airTime: NotRequired[float]
    airTimeScore: NotRequired[float]
    downlinkScore: NotRequired[float]
    linkScore: NotRequired[float]
    linkScoreHint: NotRequired[str]
    score: NotRequired[float]
    scoreMax: NotRequired[float]
    theoreticalDownlinkCapacity: NotRequired[int]
    theoreticalTotalCapacity: NotRequired[int]
    theoreticalUplinkCapacity: NotRequired[int]
    uplinkScore: NotRequired[float]


class Port1(TypedDict):
    data: Device
    matches: List["SearchResultMatch"]
    type: Literal["OtherDevice"]


class SearchResultMatch(TypedDict):
    field: NotRequired[str]
    key: NotRequired[str]
    length: NotRequired[float]
    position: NotRequired[float]
    value: NotRequired[str]


class AuthKeyMD5(TypedDict):
    id: NotRequired[int]
    key: NotRequired[str]
