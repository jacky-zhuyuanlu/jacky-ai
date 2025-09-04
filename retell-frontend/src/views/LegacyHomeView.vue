<template>
  <div id="app" class="main_bg">
    <div class="main_left">
      <div class="main_left_logo">
        <img src="/images/Logo.png" alt="">
      </div>
      <div class="main_left_menu">
        <ul>
          <li class="changeImg"><a href="#"><span class="iconimg1">消息</span></a></li>
          <li class="changeImg2"><a href="#"><span class="iconimg2">人设</span></a></li>
          <li class="changeImg3"><a href="#"><span class="iconimg3"><span class="mcp-online-indicator"></span>MCP</span></a></li>
        </ul>
      </div>
      <div class="main_left_emoji">
        <img style="padding-top: 60px; max-width: 140px;" src="/images/Normal.gif" alt="">
      </div>
    </div>
    <div class="main_right">
      <div class="top_info">
        <span class="top_info_text">消息：</span>这里是静态复制版首页，前端可自定义样式和逻辑。
      </div>
      <div class="chatmessage">
        <div class="chat-container" id="user0">
          <!-- 这里可用 Vue 组件/数据替换原有 v-for -->
          <div class="message receiver-message">
            <img class="avatar" src="/images/Fay_send.png" alt="接收者头像">
            <div class="message-content">
              <div class="message-bubble">你好，这里是复制版首页！</div>
              <div class="message-time">
                <span class="what-time">12:00</span>
                <div class="adopt-button">
                  <img src="/images/adopt.png" alt="采纳图标" class="adopt-img" />
                </div>
              </div>
            </div>
          </div>
          <div class="message sender-message">
            <div class="message-content">
              <div class="sender-message message-bubble">你好！</div>
              <div class="sender-message-time">12:01</div>
            </div>
            <img class="avatar" src="/images/User_send.png" alt="发送者头像">
          </div>
        </div>
      </div>
      <div class="inputmessage">
        <div class="inputmessage_voice">
          <img src="/images/record.png" alt="">
        </div>
        <div class="inputmessage_input">
          <textarea class="text_in" placeholder="请输入内容" style="padding-top: 13px;"></textarea>
        </div>
        <div class="inputmessage_send">
          <img src="/images/send.png" alt="发送信息">
        </div>
        <div class="inputmessage_open">
          <img src="/images/open.png">
        </div>
      </div>
      <div class="Userchange">
        <button id="prevButton">
          <img src="/images/scrollleft.png" alt="向左滑动">
        </button>
        <div class="menu">
          <div class="tag selected">用户A</div>
          <div class="tag">用户B</div>
        </div>
        <button id="nextButton">
          <img src="/images/scrollright.png" alt="向右滑动">
        </button>
      </div>
      <div class="think-panel-container">
        <div class="think-panel">
          <div class="think-panel-header">
            <h4>思考内容</h4>
            <button class="think-panel-minimize">
              <span class="think-panel-icon">-</span>
            </button>
          </div>
          <p>这里可以自定义思考内容。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 你可以在这里用 Vue 逻辑替换原有的静态内容
</script> 