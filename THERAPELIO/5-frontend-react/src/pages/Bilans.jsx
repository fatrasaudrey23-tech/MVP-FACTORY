import { motion } from "framer-motion";

export default function Bilans() {
  return (
    <div className="p-8 text-center text-thera-stabilite/60 flex-1 flex flex-col items-center justify-center">
      <motion.div
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        className="text-4xl mb-3"
      >
        📊
      </motion.div>
      <p className="text-lg font-medium">Suivi de votre état de forme et historiques à venir...</p>
    </div>
  );
}
