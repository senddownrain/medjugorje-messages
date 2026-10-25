import test from 'node:test';
import assert from 'node:assert/strict';
import { restoreNewMessages, observeArrivals, readMessage, isNewMessage } from '../../src/ui/new-messages.js';
test('first installation never flags historical or already imported messages', () => {
 const state = observeArrivals(restoreNewMessages(null), {ru:['old'],sk:['old']});
 assert.deepEqual(state.unread, []);
});
test('new message and late translation are independent, survive offline restart and old snapshot', () => {
 let state = observeArrivals(restoreNewMessages('broken'), {ru:['old']});
 state = observeArrivals(state,{ru:['old','new']});
 assert.equal(isNewMessage(state,'ru','new'),true);
 state = readMessage(state,'ru','new');
 state = observeArrivals(restoreNewMessages(JSON.stringify(state)), {ru:['old','new'],sk:['new']});
 assert.equal(isNewMessage(state,'ru','new'),false);
 assert.equal(isNewMessage(state,'sk','new'),true);
 state = observeArrivals(state,{ru:['old']});
 state = observeArrivals(state,{ru:['old','new'],sk:['new']});
 assert.equal(isNewMessage(state,'ru','new'),false);
 assert.deepEqual(state.unread,['sk/new']);
});
