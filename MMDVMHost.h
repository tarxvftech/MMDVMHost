/*
 *   Copyright (C) 2015-2021,2023 by Jonathan Naylor G4KLX
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program; if not, write to the Free Software
 *   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 */

#if !defined(MMDVMHOST_H)
#define	MMDVMHOST_H

#include "RemoteControl.h"
#include "POCSAGNetwork.h"
#include "POCSAGControl.h"
#include "DStarNetwork.h"
#include "AX25Network.h"
#include "NXDNNetwork.h"
#include "DStarControl.h"
#include "AX25Control.h"
#include "DMRControl.h"
#include "YSFControl.h"
#include "P25Control.h"
#include "NXDNControl.h"
#include "M17Control.h"
#include "NXDNLookup.h"
#include "YSFNetwork.h"
#include "P25Network.h"
#include "DMRNetwork.h"
#include "M17Network.h"
#include "FMNetwork.h"
#include "DMRLookup.h"
#include "FMControl.h"
#include "Defines.h"
#include "Timer.h"
#include "Modem.h"
#include "Conf.h"

#include <string>

class CMMDVMHost
{
public:
	CMMDVMHost(const std::string& confFile);
	~CMMDVMHost();

	int run();

	void buildNetworkStatusString(std::string &str);
	void buildNetworkHostsString(std::string &str);

private:
	CConf           m_conf;
	CModem*         m_modem;
#if defined(USE_DSTAR)
	CDStarControl*  m_dstar;
#endif
	CDMRControl*    m_dmr;
	CYSFControl*    m_ysf;
	CP25Control*    m_p25;
	CNXDNControl*   m_nxdn;
#if defined(USE_M17)
	CM17Control*    m_m17;
#endif
#if defined(USE_POCSAG)
	CPOCSAGControl* m_pocsag;
#endif
#if defined(USE_FM)
	CFMControl*     m_fm;
#endif
#if defined(USE_AX25)
	CAX25Control*   m_ax25;
#endif
#if defined(USE_DSTAR)
	CDStarNetwork*  m_dstarNetwork;
#endif
	CDMRNetwork*    m_dmrNetwork;
	CYSFNetwork*    m_ysfNetwork;
	CP25Network*    m_p25Network;
	INXDNNetwork*   m_nxdnNetwork;
#if defined(USE_M17)
	CM17Network*    m_m17Network;
#endif
#if defined(USE_POCSAG)
	CPOCSAGNetwork* m_pocsagNetwork;
#endif
#if defined(USE_FM)
	CFMNetwork*     m_fmNetwork;
#endif
#if defined(USE_AX25)
	CAX25Network*   m_ax25Network;
#endif
	unsigned char   m_mode;
#if defined(USE_DSTAR)
	unsigned int    m_dstarRFModeHang;
#endif
	unsigned int    m_dmrRFModeHang;
	unsigned int    m_ysfRFModeHang;
	unsigned int    m_p25RFModeHang;
	unsigned int    m_nxdnRFModeHang;
#if defined(USE_M17)
	unsigned int    m_m17RFModeHang;
#endif
#if defined(USE_FM)
	unsigned int    m_fmRFModeHang;
#endif
#if defined(USE_DSTAR)
	unsigned int    m_dstarNetModeHang;
#endif
	unsigned int    m_dmrNetModeHang;
	unsigned int    m_ysfNetModeHang;
	unsigned int    m_p25NetModeHang;
	unsigned int    m_nxdnNetModeHang;
#if defined(USE_M17)
	unsigned int    m_m17NetModeHang;
#endif
#if defined(USE_POCSAG)
	unsigned int    m_pocsagNetModeHang;
#endif
#if defined(USE_FM)
	unsigned int    m_fmNetModeHang;
#endif
	CTimer          m_modeTimer;
	CTimer          m_dmrTXTimer;
	CTimer          m_cwIdTimer;
	bool            m_duplex;
	unsigned int    m_timeout;
	bool            m_dstarEnabled;
	bool            m_dmrEnabled;
	bool            m_ysfEnabled;
	bool            m_p25Enabled;
	bool            m_nxdnEnabled;
	bool            m_m17Enabled;
	bool            m_pocsagEnabled;
	bool            m_fmEnabled;
	bool            m_ax25Enabled;
	unsigned int    m_cwIdTime;
	CDMRLookup*     m_dmrLookup;
	CNXDNLookup*    m_nxdnLookup;
	std::string     m_callsign;
	unsigned int    m_id;
	std::string     m_cwCallsign;
	bool            m_lockFileEnabled;
	std::string     m_lockFileName;
	CRemoteControl* m_remoteControl;
	bool            m_fixedMode;

	void readParams();
	bool createModem();
#if defined(USE_DSTAR)
	bool createDStarNetwork();
#endif
	bool createDMRNetwork();
	bool createYSFNetwork();
	bool createP25Network();
	bool createNXDNNetwork();
#if defined(USE_M17)
	bool createM17Network();
#endif
#if defined(USE_POCSAG)
	bool createPOCSAGNetwork();
#endif
#if defined(USE_FM)
	bool createFMNetwork();
#endif
#if defined(USE_AX25)
	bool createAX25Network();
#endif

	void writeSerial(const std::string& message);

	void remoteControl(const std::string& commandString);
	void processModeCommand(unsigned char mode, unsigned int timeout);
	void processEnableCommand(bool& mode, bool enabled);

	void setMode(unsigned char mode);

	void createLockFile(const char* mode) const;
	void removeLockFile() const;

	void writeJSONMode(const std::string& mode);
	void writeJSONMessage(const std::string& message);

	static void onDisplay(const std::string& message);
	static void onCommand(const std::string& command);
};

#endif
