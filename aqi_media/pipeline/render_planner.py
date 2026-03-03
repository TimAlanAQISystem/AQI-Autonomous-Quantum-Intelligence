# pipeline/render_planner.py

class RenderPlanner:
    def build_render_plan(self, scene_specs):
        plan = []
        for spec in scene_specs:
            plan.append({
                "scene_id": spec["scene_id"],
                "operations": [
                    "init_camera",
                    "apply_lighting",
                    "draw_elements",
                    "apply_motion",
                    "prepare_export"
                ],
                "duration": spec["duration"]
            })
        return plan