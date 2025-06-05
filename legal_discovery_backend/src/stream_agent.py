import asyncio
import json
import sys
import io
from contextlib import contextmanager
from typing import AsyncGenerator, Callable
import threading
import queue

class StreamCapture:
    """Capture stdout and stderr in real-time for streaming."""
    
    def __init__(self):
        self.output_queue = queue.Queue()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.capture_active = False
    
    def write(self, text):
        """Custom write method that captures output."""
        if text.strip():  # Only capture non-empty output
            self.output_queue.put(text.strip())
        # Also write to original stdout so we can see it in backend logs
        self.original_stdout.write(text)
        self.original_stdout.flush()
    
    def flush(self):
        """Flush method required by stdout interface."""
        self.original_stdout.flush()
    
    def start_capture(self):
        """Start capturing stdout."""
        self.capture_active = True
        sys.stdout = self
    
    def stop_capture(self):
        """Stop capturing stdout."""
        self.capture_active = False
        sys.stdout = self.original_stdout
    
    def get_output(self):
        """Get captured output from queue."""
        outputs = []
        while not self.output_queue.empty():
            try:
                outputs.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return outputs

async def stream_agent_execution(
    case_background: str,
    agent_function: Callable,
    config: dict
) -> AsyncGenerator[str, None]:
    """
    Stream the agent execution with real-time output capture.
    """
    
    # Create stream capture
    stream_capture = StreamCapture()
    
    try:
        # Start capturing output
        stream_capture.start_capture()
        
        # Create a flag to track completion
        execution_complete = False
        result = None
        error = None
        
        # Run the agent in a separate thread to avoid blocking
        def run_agent():
            nonlocal result, error, execution_complete
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    agent_function(case_background=case_background, config=config)
                )
            except Exception as e:
                error = e
            finally:
                execution_complete = True
        
        # Start the agent in a thread
        agent_thread = threading.Thread(target=run_agent)
        agent_thread.start()
        
        # Stream output while agent is running
        while not execution_complete:
            # Get any new output
            outputs = stream_capture.get_output()
            
            for output in outputs:
                # Parse the output and categorize it
                message_type = 'progress'
                
                # Detect different types of messages based on content
                if 'AGENT_INTRO:' in output:
                    message_type = 'agent_intro'
                    # Remove the flag prefix for cleaner display
                    output = output.replace('AGENT_INTRO: ', '')
                elif 'INSIGHT:' in output:
                    message_type = 'insight'
                elif 'KEY DISCOVERY:' in output:
                    message_type = 'discovery'
                elif 'Searched:' in output or 'Following lead:' in output or 'Conducting' in output and 'searches' in output:
                    message_type = 'search'
                elif 'RESEARCH PROGRESS:' in output or 'Research Round' in output:
                    message_type = 'research_progress'
                elif 'Decision:' in output:
                    message_type = 'decision'
                elif 'FINAL DEPOSITION STRATEGY' in output or 'Compiling deposition questions' in output:
                    message_type = 'final_strategy'
                elif 'Error' in output:
                    message_type = 'error'
                
                # Send the output
                yield f"data: {json.dumps({'type': message_type, 'message': output})}\n\n"
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        # Wait for thread to complete
        agent_thread.join()
        
        # Stop capturing
        stream_capture.stop_capture()
        
        # Get any remaining output
        outputs = stream_capture.get_output()
        for output in outputs:
            yield f"data: {json.dumps({'type': 'progress', 'message': output})}\n\n"
        
        # Handle the result
        if error:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Agent execution failed: {str(error)}'})}\n\n"
        elif result and len(result) > 0:
            final_result = {
                'type': 'complete',
                'data': {
                    'questions': result[0].get('questions', []),
                    'basis': result[0].get('basis', ''),
                    'confidence_level': result[0].get('confidence_level', 0),
                    'evidence_sources': result[0].get('evidence_sources', 0)
                },
                'message': f'Legal discovery complete! Generated {len(result[0].get("questions", []))} strategic questions.'
            }
            yield f"data: {json.dumps(final_result)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No results generated by the agent'})}\n\n"
            
    except Exception as e:
        # Make sure to stop capture on any error
        stream_capture.stop_capture()
        yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming error: {str(e)}'})}\n\n"
    
    finally:
        # Ensure capture is stopped
        if stream_capture.capture_active:
            stream_capture.stop_capture() 