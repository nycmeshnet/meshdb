import ipaddress
import re

from meshapi.types.uisp_api.devices import Device as UISPDevice
from meshapi.types.uisp_api.devices import DeviceIdentification


def management_ip(device: UISPDevice) -> str | None:
    """Prefer non-link-local management addresses, then IPv4, then UISP source order."""
    meta = device.get("meta")
    candidates = [
        device.get("ipAddress"),
        meta.get("customIpAddress") if meta else None,
        device["identification"].get("ip"),
        *(device.get("ipAddressList") or []),
    ]
    addresses = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        value = candidate.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv6Address):
            if address.scope_id:
                # A zone identifier is only meaningful on the host that reported it.
                continue
            address = address.ipv4_mapped or address
        if not (address.is_loopback or address.is_unspecified or address.is_multicast):
            addresses.append(address)

    if not addresses:
        return None
    return str(min(addresses, key=lambda address: (address.is_link_local, address.version)))


def backup_platform(identification: DeviceIdentification) -> str | None:
    """Apply the device-family rules used by the UISP-to-Oxidized inventory."""
    fields = {
        key: str(identification.get(key) or "").lower()
        for key in ("vendor", "vendorName", "platformName", "model", "modelName", "type", "name")
    }
    platform = fields["platformName"]
    hardware = " ".join(fields[k] for k in ("model", "modelName", "type")).strip()
    vendor = " ".join(fields[k] for k in ("vendor", "vendorName")).strip().strip()
    identity = f"{platform} {vendor} {hardware}"
    name = fields["name"]

    # Different Wave generations are not interchangeable. Wave MLO6 is a
    # different platform, and AP Gen2 is not yet verified with `ucfg show`.
    # Check this *before* any generic airOS 10 / Wave match below.
    if re.search(r"\bwave[ -]*(?:mlo\d*|ap[ -]*gen[ -]*2)\b", hardware):
        return None

    # Siklu EtherHaul has a built-in Oxidized model; do not confuse it
    # with the separate MultiHaul TG family (siklumhtg).
    if ("siklu" in vendor or "siklu" in platform) and re.search(
        r"\beh[ -]?\d{3,5}(?:-?fx)?(?:-[a-z0-9]+)*\b", hardware
    ):
        return "siklu"

    # Brocade / Ruckus ICX Ethernet switches run FastIron. Brocade
    # Fibre Channel switches do not and must not be inferred by vendor.
    if re.search(r"\bicx[ -]?\d{4,5}\b", hardware) or "fastiron" in platform:
        return "fastiron"

    # Fiberstore / FS.com Ethernet switch OS (FSOS). Avoid using this
    # model for a generic third-party product merely sold by FS.com.
    if "fsos" in platform or ("fiberstore" in vendor and ("internetwork" in hardware or "switch" in hardware)):
        return "fsos"

    # CSS610 is SwOS Lite, NOT RouterOS; use Oxidized's HTTP model.
    if "swos" in identity or re.search(r"\bcss\d{3,4}\b", hardware) or "css610" in hardware:
        return "swos"

    # airOS 10 / Wave: one custom Oxidized model for the Wave family.
    # Avoid matching older airFiber and airMAX on Ubiquiti vendor alone.
    if (
        "airos10" in identity
        or "airos 10" in identity
        or (hardware.strip().startswith("wave") and ("ubiquiti" in vendor or "wave" in platform or not vendor))
    ):
        return "airos10"

    if "openwrt" in identity or "openwrt" in name:
        return "openwrt"

    if any(part in identity for part in ("junos", "juniper", "qfx", "ex4300", "ex4550")):
        return "junos"

    if any(part in identity for part in ("nx-os", "nxos", "nexus", "n9k", "n7k", "n5k")):
        return "nxos"
    if "cisco" in identity:
        if any(part in identity for part in ("ios-xr", "iosxr")):
            return "iosxr"
        if any(part in identity for part in ("ios", "catalyst", "ws-c", "c3", "c9")):
            return "ios"
        return None

    if "epmp" in identity or "force 4625" in hardware:
        return "cambiumepmp"

    # APC AOS uses SSH + SCP (or FTP), not a single shell command.
    if "smart-ups" in hardware or "apc aos" in identity:
        return "apcaos"

    if "hexs - rb760igs" in hardware:
        return "routeros"

    if any(
        part in identity
        for part in ("routeros", "routerboard", "mikrotik", "microtik", "mikrotic", "mikr0tik", "routerboardos")
    ):
        return "routeros"

    # Model-specific RouterBOARD families observed in the 2026-11-14
    # NYC Mesh UISP skipped report, often with no vendor information.
    # Never infer RouterOS from *arbitrary* RB substrings.
    mikrotik_prefixes = (
        "rbomnitik",
        "rbsxt",
        "rblhg",
        "rbdisc",
        "rbgroove",
        "rbmetal",
        "rbwap",
        "rbcap",
        "rbmap",
        "rb911",
        "rb912",
        "rb922",
        "rb960",
        "rb2011",
        "rb3011",
        "rb4011",
        "rb5009",
        "ccr",
        "crs",
        "chr",
        "routeros",
        "routerboard",
    )
    model_tokens = [fields["model"], fields["modelName"]]
    if any(
        token.strip().startswith(mikrotik_prefixes) or re.fullmatch(r"ros[67] chr", token.strip())
        for token in model_tokens
    ):
        return "routeros"

    # These product names are used by RouterOS, but are not reliably
    # identified by the generic "RB" prefix in UISP.
    if any(
        token in hardware for token in ("omnitik", "sxtsq", "hap ac", "hap ax", "netmetal", "netbox", "wireless wire")
    ):
        return "routeros"

    if any(part in identity for part in ("edgeos", "edgerouter", "edgepoint r")):
        return "edgeos"
    if any(part in identity for part in ("edgeswitch", "edge switch", "es-24", "es-48")):
        return "edgeswitch"
    if any(part in identity for part in ("airfiber", "af-5", "af-24", "af60")):
        return "airfiber"
    if any(part in identity for part in ("unifi", "uap-")):
        return "unifiap"
    if any(
        part in identity
        for part in (
            "airos",
            "airmax",
            "nanostation",
            "nanobeam",
            "powerbeam",
            "litebeam",
            "liteap",
            "rocket",
            "locom5",
        )
    ):
        return "airos"

    # Wave MLO/Gen2, APC AP7752 ATS, Grandstream GWN, MoCA, Linux/VPP,
    # and unknown hardware need device-specific verification or overrides.
    return None
