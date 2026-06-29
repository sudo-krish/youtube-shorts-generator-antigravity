import re

with open('backend/modules/orchestrator/router.py', 'r') as f:
    content = f.read()

content = content.replace('from core.db.manager import db', 'from modules.orchestrator.service import orchestrator_service\nfrom modules.media.editor.service import editor_service')
content = content.replace('db.videos.get', 'editor_service.get_video')
content = content.replace('db.jobs.create', 'orchestrator_service.create_job')
content = content.replace('db.jobs.update_status', 'orchestrator_service.update_job_status')
content = content.replace('db.jobs.fail_running_stages', 'orchestrator_service.fail_running_stages')
content = content.replace('db.jobs.get_completed_stages', 'orchestrator_service.get_completed_stages')
content = content.replace('db.jobs.get_all()', 'orchestrator_service.get_all_jobs()')
content = content.replace('db.jobs.get_stages', 'orchestrator_service.get_stages')
content = content.replace('db.jobs.queue_render', 'orchestrator_service.queue_render')
content = content.replace('db.jobs.get_renders', 'orchestrator_service.get_renders')
content = content.replace('db.jobs.get', 'orchestrator_service.get_job')

with open('backend/modules/orchestrator/router.py', 'w') as f:
    f.write(content)

