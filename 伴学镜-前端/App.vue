<script>
	export default {
		onLaunch: function() {
			console.log('App Launch');
		},
		onShow: function() {
			console.log('App Show');
		},
		onHide: function() {
			console.log('App Hide');
		}
	}
</script>

<style>
	/*每个页面公共css */
	page {
		background-color: #f5f7fa;
	}

	.container {
		width: 100%;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	/* 按钮样式 */
	.btn {
		width: 100%;
		height: 45px;
		line-height: 45px;
		text-align: center;
		border-radius: 8px;
		font-size: 16px;
	}

	.btn-primary {
		background-color: #409eff;
		color: #fff;
	}

	/* 输入框样式 */
	.input {
		width: 100%;
		height: 45px;
		line-height: 45px;
		padding: 0 15px;
		background-color: #fff;
		border-radius: 8px;
		font-size: 16px;
	}

	/* 卡片样式 */
	.card {
		background-color: #fff;
		border-radius: 12px;
		padding: 20px;
		margin-bottom: 20px;
		box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
	}
</style>
