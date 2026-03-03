# pipeline/visual_composer.py

class VisualComposer:
    def __init__(self, storyboard, visual_style):
        self.storyboard = storyboard
        self.visual_style = visual_style

    def build_scene_specs(self, timeline=None):
        scene_specs = []
        num_scenes = len(self.storyboard)
        
        # Calculate scene durations based on timeline if available
        if timeline and timeline:
            total_duration = timeline[-1]["timestamp"] + 3.0 if timeline else 8.62  # Use actual audio duration
            scene_duration = total_duration / num_scenes
        else:
            scene_duration = 1.0775  # 8.62 seconds / 8 scenes
        
        for i, scene in enumerate(self.storyboard):
            # Enhanced scene spec with rich visual elements
            scene_spec = {
                "scene_id": i,
                "duration": scene_duration,  # Use calculated duration
                "background": self._generate_background(i, scene),
                "elements": self._enhance_elements(scene.get("elements", []), i),
                "animations": self._generate_animations(i),
                "style": self.visual_style,
                "description": scene.get("description", f"Scene {i+1}")
            }
            scene_specs.append(scene_spec)
        return scene_specs

    def _generate_background(self, scene_id, scene):
        """Generate sophisticated backgrounds based on scene content"""
        backgrounds = [
            # Scene 0: Deep space/tech background
            {
                "type": "gradient",
                "colors": ["#000011", "#001122", "#002244"],
                "pattern": "particles",
                "animation": "slow_drift"
            },
            # Scene 1: Warning/problem theme
            {
                "type": "gradient",
                "colors": ["#110000", "#220000", "#440000"],
                "pattern": "circuit",
                "animation": "pulse"
            },
            # Scene 2: Innovation theme
            {
                "type": "gradient",
                "colors": ["#001100", "#002200", "#004400"],
                "pattern": "matrix",
                "animation": "flow"
            },
            # Scene 3: Critical theme
            {
                "type": "gradient",
                "colors": ["#111100", "#222200", "#444400"],
                "pattern": "warning",
                "animation": "flash"
            },
            # Scene 4: Architecture theme
            {
                "type": "gradient",
                "colors": ["#000111", "#001122", "#002233"],
                "pattern": "geometric",
                "animation": "construct"
            },
            # Scene 5: Future theme
            {
                "type": "gradient",
                "colors": ["#110011", "#220022", "#440044"],
                "pattern": "nebula",
                "animation": "expand"
            },
            # Scene 6: Timeline theme
            {
                "type": "gradient",
                "colors": ["#111111", "#222222", "#333333"],
                "pattern": "timeline",
                "animation": "progress"
            },
            # Scene 7: Call to action theme
            {
                "type": "gradient",
                "colors": ["#001111", "#002222", "#004444"],
                "pattern": "portal",
                "animation": "activate"
            }
        ]
        return backgrounds[scene_id % len(backgrounds)]

    def _enhance_elements(self, elements, scene_id):
        """Add rich visual elements to text and other components"""
        enhanced = []

        for element in elements:
            if element.get("type") == "text":
                # Enhanced text with styling
                enhanced_element = {
                    "type": "text",
                    "content": element["content"],
                    "font": "Arial",
                    "size": 72,
                    "color": "#FFFFFF",
                    "shadow": True,
                    "glow": scene_id in [0, 4, 7],  # Special scenes get glow
                    "position": {"x": "(w-text_w)/2", "y": "(h-text_h)/2"},
                    "animation": "fade_in"
                }
                enhanced.append(enhanced_element)

                # Add supporting visual elements
                if scene_id == 0:  # Intro scene
                    enhanced.extend([
                        {
                            "type": "shape",
                            "shape": "circle",
                            "color": "#00FFFF",
                            "size": 200,
                            "position": {"x": "w/4", "y": "h/4"},
                            "animation": "pulse"
                        },
                        {
                            "type": "particles",
                            "count": 50,
                            "color": "#FFFFFF",
                            "speed": "slow"
                        }
                    ])
                elif scene_id == 1:  # Problem scene
                    enhanced.append({
                        "type": "icon",
                        "icon": "warning",
                        "color": "#FF0000",
                        "size": 100,
                        "position": {"x": "w/2-50", "y": "h/2+100"}
                    })
                elif scene_id == 4:  # Architecture scene
                    enhanced.extend([
                        {
                            "type": "shape",
                            "shape": "hexagon",
                            "color": "#00FF00",
                            "size": 150,
                            "position": {"x": "w*0.75", "y": "h*0.75"},
                            "animation": "rotate"
                        },
                        {
                            "type": "lines",
                            "color": "#0080FF",
                            "thickness": 3,
                            "pattern": "grid"
                        }
                    ])

        return enhanced

    def _generate_animations(self, scene_id):
        """Generate scene-specific animations"""
        animations = {
            0: ["fade_in", "particle_flow"],
            1: ["shake", "red_pulse"],
            2: ["slide_up", "green_glow"],
            3: ["zoom_in", "yellow_flash"],
            4: ["construct", "blue_flow"],
            5: ["expand", "purple_drift"],
            6: ["progress_bar", "gray_sweep"],
            7: ["portal_open", "cyan_burst"]
        }
        return animations.get(scene_id, ["fade_in"])