import json
from channels.generic.websocket import AsyncWebsocketConsumer

class LiveMonitoringConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Place all connected users (Riders, Admins, Customers) into one broadcast group
        self.group_name = 'global_live_fleet'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Remove the user from the group when they close the browser
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # 1. Receive the Base64 image frame from the Rider's frontend
        data = json.loads(text_data)

        # 2. Forward that exact frame to everyone in the 'global_live_fleet' group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_stream',
                'payload': data
            }
        )

    async def broadcast_stream(self, event):
        # 3. Push the frame down to the Admin and Customer browsers
        payload = event['payload']
        await self.send(text_data=json.dumps(payload))