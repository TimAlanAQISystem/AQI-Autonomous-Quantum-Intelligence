# integrations/video_renderer_interface.py

class VideoRenderer:
    def render_scenes(self, render_plan, scene_specs, output_dir: str):
        """
        Abstract interface for video rendering.
        - render_plan: list from RenderPlanner.build_render_plan()
        - scene_specs: list from VisualComposer.build_scene_specs()
        - output_dir: directory to place rendered scene files

        Implementation must:
          - generate one video clip per scene in output_dir
        """
        raise NotImplementedError("Video renderer integration not implemented.")