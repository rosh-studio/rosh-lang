"""
Tests for v0.3.0 Semantic Packages

Conformance tests for the semantic layer packages:
- rosh-lights: Light creation and properties
- rosh-scene: Scene environment configuration
- rosh-camera: Camera configuration and controls
- rosh-models: Model loading and properties
- rosh-data: Datasource configuration
"""

try:
    import pytest
except ImportError:
    pytest = None  # Tests can run without pytest

from src.rosh.parser import Parser
from src.rosh.lexer import Lexer
from src.rosh.ir_transformer import transform_ast_to_ir
from src.rosh.emitters.threejs import ThreeJSEmitter


def parse(source: str):
    """Helper to parse Rosh source code."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def get_emitter_output(source: str) -> str:
    """Helper to get Three.js emitter output."""
    ast = parse(source)
    ir = transform_ast_to_ir(ast)
    emitter = ThreeJSEmitter(ir, meta={'mode': 'world'})
    return emitter.emit()


# =============================================================================
# rosh-lights Tests
# =============================================================================

class TestRoshLights:
    """Tests for rosh-lights package."""

    def test_create_ambient_light(self):
        """Ambient light should be created with color and intensity."""
        program = parse("""
            create light ambient as ambient
                set color to "#404040"
                set intensity to 0.5
            end
        """)
        ir = transform_ast_to_ir(program)

        assert len(ir.objects) == 1
        obj = ir.objects[0]
        assert obj.name == "ambient"
        assert obj.type == "light"
        assert obj.parent_type == "light"
        assert obj.properties['type'].value == "ambient"

    def test_create_directional_light(self):
        """Directional light should support shadows."""
        program = parse("""
            create light sun as directional
                set color to white
                set intensity to 1.5
                set x to 50
                set y to 100
                set z to 50
                set cast_shadow to true
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.type == "light"
        assert obj.properties['type'].value == "directional"
        assert obj.properties['cast_shadow'].value == True

    def test_create_spot_light(self):
        """Spot light should support angle and penumbra."""
        program = parse("""
            create light spotlight as spot
                set color to yellow
                set intensity to 2.0
                set angle to 30
                set penumbra to 0.2
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['type'].value == "spot"
        assert obj.properties['angle'].value == 30
        assert obj.properties['penumbra'].value == 0.2

    def test_create_hemisphere_light(self):
        """Hemisphere light should support sky and ground colors."""
        program = parse("""
            create light sky as hemisphere
                set sky_color to "#87CEEB"
                set ground_color to "#8B4513"
                set intensity to 0.8
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['type'].value == "hemisphere"
        # Colors are stored as hex integers
        assert 'sky_color' in obj.properties
        assert 'ground_color' in obj.properties

    def test_create_point_light(self):
        """Point light should support distance and decay."""
        program = parse("""
            create light bulb as point
                set color to orange
                set intensity to 1.0
                set distance to 20
                set decay to 2
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['type'].value == "point"
        assert obj.properties['distance'].value == 20
        assert obj.properties['decay'].value == 2

    def test_light_emitter_output_ambient(self):
        """Emitter should generate THREE.AmbientLight."""
        output = get_emitter_output("""
            create light ambient as ambient
                set color to "#606060"
                set intensity to 1.0
            end
        """)

        assert "THREE.AmbientLight" in output
        assert "0x606060" in output

    def test_light_emitter_output_directional(self):
        """Emitter should generate THREE.DirectionalLight with shadows."""
        output = get_emitter_output("""
            create light sun as directional
                set intensity to 1.5
                set cast_shadow to true
            end
        """)

        assert "THREE.DirectionalLight" in output
        assert "castShadow = true" in output

    def test_light_emitter_output_spot(self):
        """Emitter should generate THREE.SpotLight with angle."""
        output = get_emitter_output("""
            create light spot as spot
                set angle to 45
            end
        """)

        assert "THREE.SpotLight" in output
        assert "angle = 45 * Math.PI / 180" in output

    def test_light_emitter_output_hemisphere(self):
        """Emitter should generate THREE.HemisphereLight."""
        output = get_emitter_output("""
            create light sky as hemisphere
                set sky_color to "#87CEEB"
                set ground_color to "#8B4513"
            end
        """)

        assert "THREE.HemisphereLight" in output
        assert "0x87ceeb" in output
        assert "0x8b4513" in output

    def test_light_emitter_output_point(self):
        """Emitter should generate THREE.PointLight."""
        output = get_emitter_output("""
            create light bulb as point
                set distance to 50
                set decay to 2
            end
        """)

        assert "THREE.PointLight" in output
        assert "distance = 50" in output
        assert "decay = 2" in output


# =============================================================================
# rosh-scene Tests
# =============================================================================

class TestRoshScene:
    """Tests for rosh-scene package."""

    def test_scene_background_color(self):
        """meta.scene should configure background color."""
        program = parse("""
            meta.scene
                background "#2a2a4e"
            end
        """)
        ir = transform_ast_to_ir(program)

        assert ir.metadata.extra.get('background') == "#2a2a4e"

    def test_scene_fog_properties(self):
        """meta.scene should configure fog with color, near, far."""
        program = parse("""
            meta.scene
                fog_color "#1a1a2e"
                fog_near 10
                fog_far 100
            end
        """)
        ir = transform_ast_to_ir(program)

        assert ir.metadata.extra.get('fog_color') == "#1a1a2e"
        assert ir.metadata.extra.get('fog_near') == 10
        assert ir.metadata.extra.get('fog_far') == 100

    def test_scene_emitter_background(self):
        """Emitter should set scene.background from config."""
        output = get_emitter_output("""
            meta.scene
                background "#ff0000"
            end
        """)

        assert "scene.background = new THREE.Color(0xff0000)" in output

    def test_scene_emitter_fog(self):
        """Emitter should set scene.fog from config."""
        output = get_emitter_output("""
            meta.scene
                fog_color "#000000"
                fog_near 5
                fog_far 50
            end
        """)

        assert "scene.fog = new THREE.Fog(0x000000, 5, 50)" in output

    def test_scene_default_background(self):
        """Scene should have default background if not configured."""
        output = get_emitter_output("""
            create object box
            end
        """)

        # Default background
        assert "scene.background = new THREE.Color(0x1a1a2e)" in output


# =============================================================================
# rosh-camera Tests
# =============================================================================

class TestRoshCamera:
    """Tests for rosh-camera package."""

    def test_camera_position(self):
        """meta.camera should configure camera position."""
        program = parse("""
            meta.camera
                position "10 20 30"
            end
        """)
        ir = transform_ast_to_ir(program)

        camera_config = ir.metadata.extra.get('camera', {})
        assert camera_config.get('position') == "10 20 30"

    def test_camera_target(self):
        """meta.camera should configure camera target (lookAt)."""
        program = parse("""
            meta.camera
                target "0 0 0"
            end
        """)
        ir = transform_ast_to_ir(program)

        camera_config = ir.metadata.extra.get('camera', {})
        assert camera_config.get('target') == "0 0 0"

    def test_camera_fov(self):
        """meta.camera should configure field of view."""
        program = parse("""
            meta.camera
                fov 60
            end
        """)
        ir = transform_ast_to_ir(program)

        camera_config = ir.metadata.extra.get('camera', {})
        assert camera_config.get('fov') == 60

    def test_camera_controls_orbit(self):
        """meta.camera should configure orbit controls."""
        program = parse("""
            meta.camera
                controls "orbit"
                min_distance 5
                max_distance 100
            end
        """)
        ir = transform_ast_to_ir(program)

        camera_config = ir.metadata.extra.get('camera', {})
        assert camera_config.get('controls') == "orbit"
        assert camera_config.get('min_distance') == 5
        assert camera_config.get('max_distance') == 100

    def test_camera_orbit_restrictions(self):
        """meta.camera should configure orbit restrictions."""
        program = parse("""
            meta.camera
                enable_rotate true
                enable_pan false
                enable_zoom true
            end
        """)
        ir = transform_ast_to_ir(program)

        camera_config = ir.metadata.extra.get('camera', {})
        assert camera_config.get('enable_rotate') == True
        assert camera_config.get('enable_pan') == False
        assert camera_config.get('enable_zoom') == True

    def test_camera_emitter_position(self):
        """Emitter should set camera position from config."""
        output = get_emitter_output("""
            meta.camera
                position "10 20 30"
            end
        """)

        assert "camera.position.set(10.0, 20.0, 30.0)" in output

    def test_camera_emitter_lookat(self):
        """Emitter should set camera lookAt from config."""
        output = get_emitter_output("""
            meta.camera
                target "5 5 5"
            end
        """)

        assert "camera.lookAt(5.0, 5.0, 5.0)" in output

    def test_camera_emitter_fov(self):
        """Emitter should set camera FOV from config."""
        output = get_emitter_output("""
            meta.camera
                fov 75
            end
        """)

        assert "PerspectiveCamera(75" in output

    def test_camera_emitter_distance_limits(self):
        """Emitter should set orbit control distance limits."""
        output = get_emitter_output("""
            meta.camera
                min_distance 10
                max_distance 200
            end
        """)

        assert "controls.minDistance = 10" in output
        assert "controls.maxDistance = 200" in output

    def test_camera_emitter_disable_pan(self):
        """Emitter should disable pan when configured."""
        output = get_emitter_output("""
            meta.camera
                enable_pan false
            end
        """)

        assert "controls.enablePan = false" in output


# =============================================================================
# rosh-models Tests
# =============================================================================

class TestRoshModels:
    """Tests for rosh-models package."""

    def test_model_direct_path(self):
        """Objects should support direct model path."""
        program = parse("""
            create object artifact
                set model to "models/artifact.glb"
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['model'].value == "models/artifact.glb"

    def test_model_base_scale(self):
        """Objects should support base_scale property."""
        program = parse("""
            create object artifact
                set model to "models/artifact.glb"
                set base_scale to 0.1
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['base_scale'].value == 0.1

    def test_model_world_scale(self):
        """Objects should support world_scale property."""
        program = parse("""
            create object artifact
                set model to "models/artifact.glb"
                set world_scale to 2.5
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['world_scale'].value == 2.5

    def test_model_metadata(self):
        """Objects should support model metadata properties."""
        program = parse("""
            create object artifact
                set origin to "National Museum"
                set credit to "Artist Name"
                set source to "https://example.com"
            end
        """)
        ir = transform_ast_to_ir(program)

        obj = ir.objects[0]
        assert obj.properties['origin'].value == "National Museum"
        assert obj.properties['credit'].value == "Artist Name"
        assert obj.properties['source'].value == "https://example.com"

    def test_model_emitter_direct_path(self):
        """Emitter should store model path in userData._model."""
        output = get_emitter_output("""
            create object artifact
                set model to "models/test.glb"
            end
        """)

        assert "userData._model = 'models/test.glb'" in output
        assert "userData._needsModelLoad = true" in output

    def test_model_emitter_scale_properties(self):
        """Emitter should store scale properties in userData."""
        output = get_emitter_output("""
            create object artifact
                set model to "models/test.glb"
                set base_scale to 0.5
                set world_scale to 3.0
            end
        """)

        assert "userData._baseScale = 0.5" in output
        assert "userData._worldScale = 3.0" in output

    def test_model_emitter_metadata(self):
        """Emitter should store model metadata in userData."""
        output = get_emitter_output("""
            create object artifact
                set credit to "Test Credit"
                set origin to "Test Origin"
            end
        """)

        assert "userData.credit = 'Test Credit'" in output
        assert "userData.origin = 'Test Origin'" in output


# =============================================================================
# rosh-data Tests
# =============================================================================

class TestRoshData:
    """Tests for rosh-data package."""

    def test_datasource_configuration(self):
        """meta.data should configure datasource."""
        program = parse("""
            meta.data
                name "flights"
                type "rest_api"
                url "https://api.example.com/data"
                refresh_interval 10000
            end
        """)
        ir = transform_ast_to_ir(program)

        datasources = ir.metadata.extra.get('datasources', [])
        assert len(datasources) == 1
        ds = datasources[0]
        assert ds['name'] == "flights"
        assert ds['type'] == "rest_api"
        assert ds['url'] == "https://api.example.com/data"
        assert ds['refresh_interval'] == 10000

    def test_datasource_fallback(self):
        """meta.data should support fallback configuration."""
        program = parse("""
            meta.data
                name "api"
                url "https://api.example.com"
                fallback "sample_data"
            end
        """)
        ir = transform_ast_to_ir(program)

        datasources = ir.metadata.extra.get('datasources', [])
        assert datasources[0]['fallback'] == "sample_data"

    def test_multiple_datasources(self):
        """Multiple meta.data blocks should create multiple datasources."""
        program = parse("""
            meta.data
                name "source1"
                url "https://api1.example.com"
            end

            meta.data
                name "source2"
                url "https://api2.example.com"
            end
        """)
        ir = transform_ast_to_ir(program)

        datasources = ir.metadata.extra.get('datasources', [])
        assert len(datasources) == 2
        assert datasources[0]['name'] == "source1"
        assert datasources[1]['name'] == "source2"

    def test_datasource_emitter_config(self):
        """Emitter should generate datasource config object."""
        output = get_emitter_output("""
            meta.data
                name "flights"
                type "rest_api"
                url "https://api.example.com/data"
            end
        """)

        assert "const flights_config = {" in output
        assert "url: 'https://api.example.com/data'" in output

    def test_datasource_emitter_fetch_function(self):
        """Emitter should generate fetch function."""
        output = get_emitter_output("""
            meta.data
                name "mydata"
                url "https://api.example.com"
            end
        """)

        assert "async function fetch_mydata()" in output
        assert "await fetch(mydata_config.url)" in output

    def test_datasource_emitter_auto_refresh(self):
        """Emitter should set up auto-refresh when interval > 0."""
        output = get_emitter_output("""
            meta.data
                name "live"
                url "https://api.example.com"
                refresh_interval 5000
            end
        """)

        assert "setInterval(fetch_live, 5000)" in output
        assert "fetch_live();  // Initial fetch" in output

    def test_datasource_emitter_no_refresh_when_zero(self):
        """Emitter should not set up refresh when interval is 0."""
        output = get_emitter_output("""
            meta.data
                name "static"
                url "https://api.example.com"
                refresh_interval 0
            end
        """)

        assert "setInterval" not in output or "setInterval(fetch_static" not in output


# =============================================================================
# Integration Tests
# =============================================================================

class TestSemanticPackageIntegration:
    """Integration tests combining multiple semantic packages."""

    def test_complete_scene_setup(self):
        """Full scene with lights, camera, and background."""
        output = get_emitter_output("""
            meta.scene
                background "#000033"
                fog_color "#000033"
                fog_near 20
                fog_far 200
            end

            meta.camera
                position "0 10 50"
                target "0 0 0"
                fov 60
            end

            create light sun as directional
                set intensity to 1.5
                set cast_shadow to true
            end

            create light ambient as ambient
                set intensity to 0.3
            end
        """)

        # Scene
        assert "scene.background = new THREE.Color(0x000033)" in output
        assert "scene.fog = new THREE.Fog(0x000033, 20, 200)" in output

        # Camera
        assert "PerspectiveCamera(60" in output
        assert "camera.position.set(0.0, 10.0, 50.0)" in output

        # Lights
        assert "THREE.DirectionalLight" in output
        assert "THREE.AmbientLight" in output

    def test_museum_style_scene(self):
        """Museum-style scene with models and spotlights."""
        output = get_emitter_output("""
            meta.scene
                background "#1a1a1a"
            end

            meta.camera
                controls "orbit"
                min_distance 2
                max_distance 20
            end

            create light spot1 as spot
                set color to white
                set intensity to 2.0
                set angle to 30
            end

            create object artifact
                set model to "models/artifact.glb"
                set base_scale to 0.1
                set origin to "Museum Collection"
            end
        """)

        assert "THREE.SpotLight" in output
        assert "userData._model = 'models/artifact.glb'" in output
        assert "userData._baseScale = 0.1" in output
        assert "controls.minDistance = 2" in output

    def test_data_visualization_scene(self):
        """Data visualization scene with datasource."""
        output = get_emitter_output("""
            meta.scene
                background "#000022"
            end

            meta.camera
                position "0 50 0"
                target "0 0 0"
                enable_rotate false
            end

            meta.data
                name "flights"
                type "rest_api"
                url "https://api.example.com/flights"
                refresh_interval 10000
            end
        """)

        assert "scene.background = new THREE.Color(0x000022)" in output
        assert "camera.position.set(0.0, 50.0, 0.0)" in output
        assert "controls.enableRotate = false" in output
        assert "const flights_config = {" in output
        assert "setInterval(fetch_flights, 10000)" in output
