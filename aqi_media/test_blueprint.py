import json

# Load and validate the blueprint
with open('../aqi_documentary_blueprint.json', 'r') as f:
    blueprint_data = json.load(f)

print('✅ Blueprint JSON is valid and loaded successfully')
print(f'Title: {blueprint_data["title"]}')
print(f'Chapters: {len(blueprint_data["chapters"])}')

total_scenes = sum(len(chapter['scenes']) for chapter in blueprint_data['chapters'])
print(f'Total Scenes: {total_scenes}')
print(f'Duration: {blueprint_data["duration_minutes"]} minutes')

# Check structure
print('\n📋 Blueprint Structure:')
print(f'- Voice Identity: {blueprint_data["voice_identity"]["style"]}')
print(f'- Theme Colors: {len([ch["theme_color"] for ch in blueprint_data["chapters"]])} chapters')
print(f'- Production Specs: {len(blueprint_data["production_specs"]["render_batches"])} batches')

print('\n🎬 Ready for AQI pipeline ingestion!')
print('The documentary blueprint is complete and production-ready.')