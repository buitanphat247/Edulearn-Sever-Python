from flask_socketio import emit, join_room, leave_room
from flask import request
from src.services.exam_generation_service.exam_service import ExamService

# Initialize Service
exam_service = ExamService()

def register_socket_events(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on('join_attempt')
    def handle_join_attempt(data):
        """
        data: { 'attemptId': str }
        """
        attempt_id = data.get('attemptId')
        if not attempt_id:
            return
            
        room = f"attempt_{attempt_id}"
        join_room(room)
        
        # Sync time immediately
        res = exam_service.get_remaining_time(attempt_id)
        emit('time_sync', res, room=request.sid)
        
        print(f"User joined attempt room: {room}")

    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """
        data: { 'attemptId': str }
        """
        attempt_id = data.get('attemptId')
        if not attempt_id:
            return
            
        # Update DB and check expiration
        res = exam_service.update_heartbeat(attempt_id)
        
        # If expired, notify the client
        if res.get("is_expired"):
            emit('time_up', res, room=f"attempt_{attempt_id}")
        else:
            # Send back sync info
            emit('time_sync', res, room=request.sid)

    @socketio.on('save_answers')
    def handle_save_answers(data):
        attempt_id = data.get('attemptId')
        answers = data.get('answers')
        if not attempt_id or answers is None:
            return
            
        # Update DB in real-time
        exam_service.save_answers(attempt_id, answers)
        print(f"Answers autosaved for attempt: {attempt_id}")

    @socketio.on('report_violation')
    def handle_violation(data):
        """
        data: { 'attemptId': str, 'type': str, 'message': str }
        """
        attempt_id = data.get('attemptId')
        v_type = data.get('type')
        msg = data.get('message')
        
        if attempt_id:
            exam_service.log_security_event(attempt_id, v_type, msg)
        
        # Acknowledge
        emit('violation_recorded', {'status': 'ok'}, room=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid}")
