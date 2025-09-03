<script lang="ts">
	let wsUrl = $state('');
	let ws: WebSocket;
	let messages: string[] = $state([]);
	let message = $state('');

	const sendMessage = () => {
		ws.send(message);
		message = '';
	};

	const credentials = $state({
		name: '',
		password: ''
	});

	const baseAddress = 'https://expand-farmer-contacted-italiano.trycloudflare.com';

	const connect = async () => {
		const formData = new FormData();

		formData.append('username', credentials.name);
		formData.append('password', credentials.password);

		const loginTokens = await fetch(`${baseAddress}/login`, {
			method: 'POST',
			body: formData
		});

		const loginData = await loginTokens.json();

		const accessToken = loginData.access_token;

		const matchMake = await fetch(`${baseAddress}/match/make`, {
			headers: {
				Authorization: `Bearer ${accessToken}`
			}
		});
		const data = await matchMake.json();

		const potentialWsUrl = data.ws_url;

		if (!potentialWsUrl) {
			return;
		}

		wsUrl = potentialWsUrl;

		const params = new URLSearchParams({
			token: accessToken
		});

		ws = new WebSocket(wsUrl + '?' + params.toString());

		ws.onmessage = (event) => {
			messages.push(event.data);
		};

		ws.onopen = () => {
			console.log(`Connected to ${wsUrl}`);
		};

		ws.onclose = () => {
			console.log(`Disconnected from ${wsUrl}`);
		};
	};
</script>

<div class="grid grid-cols-2">
	<div>
		<input
			type="text"
			class="m-3 rounded-lg border-2 border-black bg-gray-300 p-2"
			bind:value={message}
		/>
		<!-- svelte-ignore a11y_consider_explicit_label -->
		<button
			class="m-3 rounded-lg border-2 border-black bg-gray-300 p-2"
			onclick={() => sendMessage()}>Send</button
		>
		<ul class="ml-10 list-disc text-xl">
			{#each messages as msg}
				<li>{msg}</li>
			{/each}
		</ul>
	</div>
	<div>
		<input
			type="text"
			class="m-3 border-2 border-black bg-gray-300 p-1"
			bind:value={credentials.name}
			placeholder="Name"
		/>
		<input
			type="text"
			class="m-3 border-2 border-black bg-gray-300 p-1"
			bind:value={credentials.password}
			placeholder="Password"
		/>
		<!-- svelte-ignore a11y_consider_explicit_label -->
		<button onclick={() => connect()} class="m-3 border-2 border-black bg-gray-300 p-1"
			>Connect</button
		>
	</div>
</div>
