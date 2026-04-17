import uuid
from flask import Blueprint, jsonify, request
from .services.executor import QueueFull

def routes(store, executor):
    api=Blueprint('scenes',__name__,url_prefix='/api')

    def body():
        data=request.get_json(silent=True)
        if not isinstance(data,dict): raise ValueError('A JSON object is required.')
        return data

    @api.errorhandler(ValueError)
    def invalid(exc): return jsonify(error=str(exc)),400
    @api.errorhandler(QueueFull)
    def full(exc): return jsonify(error=str(exc)),429
    @api.errorhandler(RuntimeError)
    def unavailable(exc): return jsonify(error=str(exc)),502

    @api.get('/scenes')
    def scenes(): return jsonify(store.scenes())

    @api.post('/scenes')
    def save():
        data=body()
        name=data.get('name','')
        if not isinstance(name,str) or not 1<=len(name.strip())<=100: raise ValueError('Scene name is required.')
        version=data.get('version',0)
        if type(version) is not int or version<0: raise ValueError('Invalid scene version.')
        scene_id=data.get('id') or str(uuid.uuid4())
        if not isinstance(scene_id,str) or len(scene_id)>80: raise ValueError('Invalid scene ID.')
        return jsonify(store.save_scene(scene_id,name.strip(),executor.validate(data.get('targets')),version)),201

    @api.post('/scenes/<scene_id>/execute')
    def execute(scene_id):
        scene=next((s for s in store.scenes() if s['id']==scene_id),None)
        if scene is None: return jsonify(error='Scene not found.'),404
        return jsonify(executor.submit(scene['targets'],request.headers.get('Idempotency-Key'))),202

    @api.post('/groups/volume')
    def group_volume():
        data=body()
        ids=data.get('players')
        if not isinstance(ids,list): raise ValueError('players must be an array.')
        targets=[{'entity_id':entity,'volume':data.get('volume'),'state':'unchanged'} for entity in ids]
        return jsonify(executor.submit(targets,request.headers.get('Idempotency-Key'))),202

    @api.get('/jobs')
    def jobs(): return jsonify(store.jobs())

    @api.get('/jobs/<job_id>')
    def job(job_id):
        rows=store.jobs(job_id)
        return jsonify(rows[0]) if rows else (jsonify(error='Job not found.'),404)
    return api
