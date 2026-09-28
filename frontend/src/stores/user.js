import { defineStore } from 'pinia'
import api from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null
  }),

  getters: {
    isLoggedIn: (state) => !!state.token
  },

  actions: {
    async login(credentials) {
      const response = await api.auth.login(credentials)
      this.token = response.access_token
      localStorage.setItem('token', this.token)
      await this.fetchUserInfo()
    },

    async fetchUserInfo() {
      this.userInfo = await api.auth.me()
    },

    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
    }
  }
})
