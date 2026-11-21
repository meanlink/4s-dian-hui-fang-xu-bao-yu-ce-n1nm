export const state = {token: localStorage.getItem('dealer-token'), session: null, dashboard:null, owners:[], services:[], leads:[], followups:[]};
export function setToken(token){state.token=token;if(token)localStorage.setItem('dealer-token',token);else localStorage.removeItem('dealer-token');}
