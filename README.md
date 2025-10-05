#S.M.A.L.L-E

Smart Multisensory Autonomous Learning Lifeform – Edge

Inspiration

We wanted to explore what happens when artificial intelligence can not only think and speak, but also see and respond to the people around it. Our team envisioned an interactive, physical assistant that merges computer vision, language models, and speech synthesis into one friendly, real-world presence.

What it does

S.M.A.L.L-E is an interactive AI robot that can see, listen, and respond like a human companion. It:

Recognizes and tracks faces

Listens to speech

Replies in real time with natural conversation and expressive voice

The camera is mounted on a movable servo, allowing the robot to physically turn toward whoever is speaking, creating the sense of genuine attention and awareness. Together, these elements make for a small yet lively assistant capable of holding meaningful dialogue in its environment.

How we built it

We combined several frameworks and devices to bring S.M.A.L.L-E to life. Two Jetson Xavier NX boards handled vision and speech recognition tasks, sending processed data to a Raspberry Pi that controlled the servo-mounted camera. This coordination allowed the robot to orient toward a speaker while maintaining smooth, real-time interaction.

Key Components

DeepFace – Facial detection and tracking

Jetson Xavier NX – Speech recognition and transmitting camera data to Raspberry Pi

Raspberry Pi + Servo Motors – Camera motion control

Whisper – Speech-to-text processing

Gemini API – Intelligent language understanding and response generation

ElevenLabs API – Realistic text-to-speech output

Python 3.11/3.12 & VS Code – Integration and testing

The system communicates through lightweight network calls between the camera module, Jetson units, and Raspberry Pi’s control program, forming a unified audio–visual interaction pipeline.

Challenges we ran into

Version control and coordination between Jetson boards

Communication latency between Jetsons and servo control

Integrating multiple hardware and cloud APIs in real time

Accomplishments

We’re proud to have delivered a fully functional AI companion that allows hardware and AI to interact seamlessly with its environment and users.

What we learned

Deepened understanding of multimodal AI systems

Learned about asynchronous hardware-software communication

Gained experience with reproducible environment setup

Hands-on practice integrating vision, audio, and language into a cohesive user experience

What's next for S.M.A.L.L-E

Our goal is to evolve S.M.A.L.L-E into a more advanced, specialized assistant, capable of adapting to specific tasks or environments, and further improving its emotional intelligence, interaction quality, and autonomy.
