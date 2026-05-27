from typing import Optional


class ProviderCandidate:
    def __init__(
        self,
        provider_id:    str,
        source:         str,
        npi:            str,
        name:           str,
        specialty:      str,
        city:           str,
        state:          str,
        latitude:       Optional[float],
        longitude:      Optional[float],
        network_status: str,
        zipcode:        str = "",
        address_line:   str = "",
        organization:   str = "",
    ):
        self.provider_id    = provider_id
        self.source         = source
        self.npi            = npi
        self.name           = name
        self.specialty      = specialty
        self.city           = city
        self.state          = state
        self.zipcode        = zipcode
        self.address_line   = address_line
        self.organization   = organization
        self.latitude       = latitude
        self.longitude      = longitude
        self.network_status = network_status

    def to_dict(self) -> dict:
        return {
            "provider_id":    self.provider_id,
            "source":         self.source,
            "npi":            self.npi,
            "name":           self.name,
            "specialty":      self.specialty,
            "organization":   self.organization,
            "address": {
                "line":       self.address_line,
                "city":       self.city,
                "state":      self.state,
                "zipcode":    self.zipcode,
                "latitude":   self.latitude,
                "longitude":  self.longitude,
            },
            "network_status": self.network_status,
        }
