class MapManager:
    """Generazione della mappa interattiva (Leaflet + GeoJSON)."""

    @staticmethod
    def get_map_html() -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body { margin: 0; padding: 0; background-color: #ecf0f1; }
                #map { height: 100vh; width: 100vw; }
                .leaflet-container { font-family: Arial, sans-serif; }
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map', { zoomControl: false }).setView([20.0, 0.0], 2);
                L.control.zoom({ position: 'bottomright' }).addTo(map);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: 'abcd', maxZoom: 19, minZoom: 2
                }).addTo(map);

                let selectedLayer = null;
                let countryLocked = false; 
                let globalGeojsonLayer = null;

                window.lockCountryUI = function(countryName) { countryLocked = true; };
                window.unlockCountryUI = function() {
                    countryLocked = false;
                    if (selectedLayer && globalGeojsonLayer) {
                        globalGeojsonLayer.resetStyle(selectedLayer);
                        selectedLayer = null;
                    }
                };

                fetch('https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json')
                    .then(response => response.json())
                    .then(data => {
                        globalGeojsonLayer = L.geoJson(data, {
                            style: function (feature) { return { color: "#2980b9", weight: 1, fillOpacity: 0.1, fillColor: "#3498db" }; },
                            onEachFeature: function (feature, layer) {
                                layer.on('mouseover', function () { if (selectedLayer !== this && !countryLocked) this.setStyle({ fillOpacity: 0.4 }); });
                                layer.on('mouseout', function () { if (selectedLayer !== this && !countryLocked) this.setStyle({ fillOpacity: 0.1 }); });

                                // TASTO SINISTRO: Selezione Nazione
                                layer.on('click', function () {
                                    console.log("COUNTRY_SELECTED:" + feature.properties.name);
                                    if (!countryLocked) {
                                        if (selectedLayer) globalGeojsonLayer.resetStyle(selectedLayer);
                                        selectedLayer = this;
                                        this.setStyle({ fillOpacity: 0.7, fillColor: "#e74c3c", color: "#c0392b", weight: 2 });
                                    }
                                });

                                // TASTO DESTRO: Intelligence e Azioni Mirate
                                layer.on('contextmenu', function (e) {
                                    console.log("COUNTRY_RIGHT_CLICKED:" + feature.properties.name);
                                });
                            }
                        }).addTo(map);
                    })
                    .catch(error => console.error('Errore GeoJSON:', error));
            </script>
        </body>
        </html>
        """